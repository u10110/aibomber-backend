import os

from minio import Minio
from decouple import config


# MINIO_ENDPOINT=config("MINIO_ENDPOINT")
# MINIO_ACCESS_KEY = config("MINIO_ACCESS_KEY")
# MINIO_SECRET_KEY=config("MINIO_SECRET_KEY")
# region = config("MINIO_REGION")


class MinioService:

    def __init__(self):

        self.client = Minio(
            endpoint=config("MINIO_ENDPOINT"),
            access_key=config("MINIO_ACCESS_KEY"),
            secret_key=config("MINIO_SECRET_KEY"),
            secure=False,
            region=config("MINIO_REGION")
        )

    def put_object(self, obj_name, path):
        self.client.fput_object('review-images', obj_name, path)

    def get_obj(self, obj_name, path):
        self.client.fget_object('review-images', obj_name, path)

    def remove_obj(self, obj_name):
        self.client.remove_object('review-images', obj_name)