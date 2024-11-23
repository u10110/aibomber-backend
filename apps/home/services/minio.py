import os

from decouple import config

from minio import Minio


class MinioService:
    def __init__(self):
        self.client = Minio(
            endpoint=config("MINIO_ENDPOINT"),
            access_key=config("MINIO_ACCESS_KEY"),
            secret_key=config("MINIO_SECRET_KEY"),
            secure=False,
            region=config("MINIO_REGION"),
        )

    def put_object(self, obj_name, path):
        self.client.fput_object("wb-profiles", obj_name, path)

    def get_obj(self, obj_name, path):
        self.client.fget_object("wb-profiles", obj_name, path)

    def list_obj(self):
        return self.client.list_objects("wb-profiles")
