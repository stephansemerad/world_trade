import requests
import polars as pl
import xmltodict
from rich import print
import pycountry
import pycountry_convert as pc
from datetime import date, datetime


def build_lookup() -> dict:
    lookup = {}
    for c in pycountry.countries:
        try:
            alpha_2 = pc.country_alpha3_to_country_alpha2(c.alpha_3)
            continent_code = pc.country_alpha2_to_continent_code(alpha_2)
            region = pc.convert_continent_code_to_continent_name(continent_code)
        except Exception:
            region = None

        lookup[c.alpha_3] = {
            "country_name": c.name,
            "region": region,
        }
    return lookup


lookup = build_lookup()


# https://medium.com/@amuhryanto/pulling-trade-data-from-the-wb-wits-api-using-python-1787393f8330

BASE_URL = "http://wits.worldbank.org/API/V1/SDMX/V21/rest"
DATASET_ID = "DF_WITS_TradeStats_Trade"
DATASTRUCTURE_ID = "TRADESTATS"


class WorldTrade:

    def __init__(self):
        self.countries = self.get_codelist("CL_TS_COUNTRY_WITS")
        self.products = self.get_codelist("CL_TS_PRODUCTCODE_WITS")
        self.indicators = self.get_codelist("CL_TS_INDICATOR_WITS")
        self.start = 2010
        self.end = 2020

        self.exporting = "USD"
        self.importing = "MXN"
        self.product = "27-27_Fuels"
        self.indicator = "XPRT-TRD-VL"
        self.frequency = "A"

    # ------------------------------------------------------------------ #
    # Helpers                                                              #
    # ------------------------------------------------------------------ #

    def _fetch_xml(self, path: str) -> dict:
        response = requests.get(path)
        response.raise_for_status()
        return xmltodict.parse(response.text)["Structure"]

    def _parse_codelist(self, codes) -> pl.DataFrame:
        if isinstance(codes, dict):
            codes = [codes]

        return pl.DataFrame(
            [{"id": c["@id"], "name": c["Name"]["#text"]} for c in codes]
        )

    def get_codelist(self, codelist_id: str) -> pl.DataFrame:
        data = self._fetch_xml(f"{BASE_URL}/codelist/WBG_WITS/{codelist_id}")
        codes = data["Structures"]["Codelists"]["Codelist"]["Code"]

        df = self._parse_codelist(codes)
        if codelist_id == "CL_TS_COUNTRY_WITS":
            df = df.with_columns(
                [
                    pl.col("id")
                    .map_elements(
                        lambda x: lookup.get(x, {}).get("region"), return_dtype=pl.Utf8
                    )
                    .alias("region"),
                ]
            )

        return df

    def query(self) -> pl.DataFrame:

        query_string = ".".join(
            [
                self.frequency,
                self.exporting,
                self.importing,
                self.product,
                self.indicator,
            ]
        )
        path = f"{BASE_URL}/data/{DATASET_ID}/{query_string}?startperiod={self.start}&endperiod={self.end}"
        print(path)

        response = requests.get(path)
        print(response.status_code, response.reason)

        if response.status_code != 200:
            return pl.DataFrame()

        series_list = xmltodict.parse(response.text)["message:GenericData"][
            "message:DataSet"
        ]["generic:Series"]
        if isinstance(series_list, dict):
            series_list = [series_list]

        rows = []
        for series in series_list:
            key_values = series["generic:SeriesKey"]["generic:Value"]
            if isinstance(key_values, dict):
                key_values = [key_values]
            series_dims = {v["@id"]: v["@value"] for v in key_values}

            obs_list = series["generic:Obs"]
            if isinstance(obs_list, dict):
                obs_list = [obs_list]

            for obs in obs_list:
                period = obs["generic:ObsDimension"]["@value"]
                value = float(obs["generic:ObsValue"]["@value"])

                attrs = obs.get("generic:Attributes", {}).get("generic:Value", [])
                if isinstance(attrs, dict):
                    attrs = [attrs]
                obs_attrs = {a["@id"]: a["@value"] for a in attrs}

                rows.append(
                    {**series_dims, "period": period, "value": value, **obs_attrs}
                )

        return pl.DataFrame(rows)


if __name__ == "__main__":
    w = WorldTrade()

    countries_df = w.countries.filter(pl.col("region").is_null())
    print(countries_df)
