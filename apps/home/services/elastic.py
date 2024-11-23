import json
import os
from datetime import date

from decouple import config
from elasticsearch import Elasticsearch, helpers


class ES:
    def __init__(self):
        host = config("ELASTIC_HOST")
        self.es = Elasticsearch([host])

    def docs_create(self, actions):
        # resp = self.es.index(index='goods', doc_type='sentences', document=doc)
        resp = helpers.bulk(self.es, actions, index="phrase", request_timeout=300)
        return resp

    def get_doc(self, imtId):
        """get doc from index"""
        response = self.es.search(
            index="goods", body={"size": 1, "query": {"term": {"root": imtId}}}
        )
        doc = response["hits"]["position"]
        return doc

    def get_phrases(self, sku):
        response = self.es.get(index="reviews", id=sku)
        return response

    def get_doc_by_sku(self, sku, type=None):
        """get doc from index"""
        doc = []

        # index_list = self.es.indices.get("position")
        for i in range(0, 10):
            if i == 0:
                index = "positions"
            else:
                index = "positions" + str(i)
            if self.es.exists(index=index, id=sku):
                response = self.es.get(index=index, id=sku)
                for p in response["_source"]["positions"]:
                    doc.append(p)
        return doc

    def get_uniq(self):
        response = self.es.search(
            index="goods",
            body={
                "size": 0,
                "aggs": {"langs": {"terms": {"field": "root", "size": 999999}}},
            },
            request_timeout=130,
        )
        docs = response["aggregations"]["langs"]["buckets"]
        with open(r"roots.txt", "w", encoding="utf8") as f:
            for doc in docs:
                root = doc["key"]
                f.write(f"{root}\n")
        return docs

    # def add_positions(self, data):
    #     date_now = date.today()
    #     for sku in data.keys():
    #         phrases = data[sku]
    #         body = {
    #             "script": {
    #                 "source": "if (!(ctx._source.positions instanceof Collection)) {ctx._source.positions = [ctx._source.positions];} ctx._source.positions.add(params.positions)",
    #                 "params": {
    #                     "positions": {
    #                         "date": date_now,
    #                         "phrases": phrases,
    #                     }
    #                 },
    #             }
    #         }
    #         print(self.es.exists(index="goods2", id=sku))
    #         if self.es.exists(index="goods2", id=sku):
    #             self.es.update(index="goods2", id=sku, body=body)
    #         else:
    #             body = {
    #                 "positions": {
    #                     "date": date_now,
    #                     "phrases": phrases,
    #                 }
    #             }

    #             self.es.index(index="goods2", id=sku, document=body)
    @staticmethod
    def add_positions(doc):
        host = config("ELASTIC_HOST")
        es = Elasticsearch([host])
        date_now = date.today()
        sku = doc["id"]
        print(sku)
        if es.exists(index="goods2", id=sku):
            es.update(index="goods2", id=sku, body=doc["script"])
        elif "params" in doc["script"]:
            body = {
                "positions": {
                    "date": date_now,
                    "phrases": doc["script"]["params"],
                }
            }
            es.index(index="goods2", id=sku, document=doc["script"])
