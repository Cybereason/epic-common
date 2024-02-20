import os

import pytest
from pathlib import Path
from google.cloud import storage

from epic.common.pathgeneralizer import PathGeneralizer, FileSystemPath, GoogleCloudStoragePath


class TestPathGeneralizer:
    def test_from_path(self):
        assert isinstance(PathGeneralizer.from_path("x:\\windows.txt"), FileSystemPath)
        assert isinstance(PathGeneralizer.from_path("/tmp/path/mydata"), FileSystemPath)
        assert isinstance(PathGeneralizer.from_path("/Users/joe/Music"), FileSystemPath)
        assert isinstance(PathGeneralizer.from_path("README.md"), FileSystemPath)
        assert isinstance(PathGeneralizer.from_path(Path("README.md")), FileSystemPath)
        assert isinstance(PathGeneralizer.from_path("gs://gcs-bucket/path"), GoogleCloudStoragePath)
        assert isinstance(PathGeneralizer.from_path(PathGeneralizer.from_path("file")), FileSystemPath)
        assert isinstance(PathGeneralizer.from_path(PathGeneralizer.from_path("gs://bucket/x")), GoogleCloudStoragePath)
        with pytest.raises(ValueError):
            PathGeneralizer.from_path("gxs://gcs-bucket")
        with pytest.raises(ValueError):
            PathGeneralizer.from_path("gs://")
        with pytest.raises(ValueError):
            PathGeneralizer.from_path("bugs://not-a-gcs-bucket")
        with pytest.raises(ValueError):
            PathGeneralizer.from_path("")
        with pytest.raises(TypeError):
            PathGeneralizer.from_path(None)
        with pytest.raises(TypeError):
            PathGeneralizer.from_path(100)

    def test_files(self, tmp_path):
        path = os.path.join(tmp_path, "file")
        open(path, "w").write("contents")
        assert PathGeneralizer.from_path(path).read("r") == "contents"
        assert PathGeneralizer.from_path(path).read("r", 100) == "contents"
        assert PathGeneralizer.from_path(path).read("r", len("contents")) == "contents"
        assert PathGeneralizer.from_path(path).read("r", 4) == "cont"
        pg = PathGeneralizer.from_path(path)
        assert pg.read("r") == "contents"
        assert pg.read("r") == "contents"
        cwd = os.getcwd()
        os.chdir(tmp_path)
        try:
            assert PathGeneralizer.from_path("file").read("r") == "contents"
        finally:
            os.chdir(cwd)
        assert PathGeneralizer.from_path(path).exists()
        assert not PathGeneralizer.from_path(os.path.join(tmp_path, "nofile")).exists()
        assert not PathGeneralizer.from_path("nofile").exists()
        os.remove(path)
        assert not pg.exists()
        pg.write("hello", "w")
        assert pg.exists()
        assert os.path.exists(path)
        assert pg.read("r") == "hello"
        pg.write("world", "a")
        assert pg.exists()
        assert os.path.exists(path)
        assert pg.read("r") == "helloworld"
        pg.write("bye", "w")
        assert pg.exists()
        assert os.path.exists(path)
        assert pg.read("r") == "bye"
        os.remove(path)
        with pg.write_proxy() as proxy_path:
            open(proxy_path, "w").write("one")
        assert pg.read("r") == "one"
        assert pg.exists()
        assert os.path.exists(path)
        with pg.read_proxy() as proxy_path:
            assert open(proxy_path, "r").read() == "one"
        assert pg.read("r") == "one"
        with pg.read_write_proxy() as proxy_path:
            assert open(proxy_path, "r").read() == "one"
            with open(proxy_path, "r+") as f:
                f.seek(1)
                f.write("xygen")
                f.seek(3)
                f.truncate()
        assert pg.read("r") == "oxy"
        path2 = os.path.join(tmp_path, "file2")
        assert not os.path.exists(path2)
        pg.copy_to(path2)
        assert os.path.exists(path2)
        os.remove(path)
        PathGeneralizer.from_path(path2).copy_to(path)
        assert os.path.exists(path)

    def test_google_cloud_storage(self, tmp_path):
        # for testsing
        GoogleCloudStoragePath._cached_gs_client = storage.Client.create_anonymous_client()
        GoogleCloudStoragePath._cached_gs_client_pid = os.getpid()

        assert not PathGeneralizer.from_path("gs://gcp-public-data-landsat/no-such-file").exists()
        assert not PathGeneralizer.from_path("gs://no-such-bucket/nothing-here").exists()

        # actual files from Google public data
        pg1 = PathGeneralizer.from_path("gs://gcp-public-data-landsat/index.csv.gz")
        assert pg1.exists()
        assert pg1.read("rb", 10) == b'\x1f\x8b\x08\x08L\xde\xe8a\x02\xff'
        pg2 = PathGeneralizer.from_path(
            "gs://gcp-public-data-landsat/LC08/01/001/003/LC08_L1GT_001003_20140812_20170420_01_T2/"
            "LC08_L1GT_001003_20140812_20170420_01_T2_MTL.txt"
        )
        assert pg2.exists()
        assert pg2.read("r")[:24] == "GROUP = L1_METADATA_FILE"
        data = pg2.read("r")
        assert len(data) == 8439
        data_b = pg2.read("rb")
        assert len(data_b) == 8439
        assert data.encode("ascii") == data_b
        with pg2.read_proxy() as local_path:
            assert open(local_path, "r").read() == data
        path = os.path.join(tmp_path, "file")
        pg2.copy_to(path)
        assert open(path, "r").read() == data
