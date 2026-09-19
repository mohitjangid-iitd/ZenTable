"""
tests/test_blog_images.py — Tests for blog image upload, storage, and cleanup.
"""

import io
import os
from unittest.mock import patch, MagicMock
import pytest
from fastapi.testclient import TestClient
from main import app
from routers.blog import delete_blog_image

@pytest.fixture
def client():
    return TestClient(app)

@pytest.fixture
def mock_admin_auth():
    with patch("routers.blog._require_blog_access", return_value={"role": "admin", "name": "Admin", "admin_id": 1}), \
         patch("routers.blog._require_admin", return_value={"role": "admin", "name": "Admin", "admin_id": 1}):
        yield

def test_upload_blog_image_local(client, mock_admin_auth):
    """Local mode (USE_R2=False) should save to static/blog/"""
    file_content = b"fake_png_data"
    with patch("routers.blog.USE_R2", False):
        res = client.post(
            "/api/blog/upload-image",
            files={"file": ("test_art.png", io.BytesIO(file_content), "image/png")}
        )
    assert res.status_code == 200
    data = res.json()
    assert data["success"] is True
    assert data["url"].startswith("/static/blog/")

    # Check file exists and cleanup
    local_path = os.path.join("static", "blog", data["filename"])
    assert os.path.exists(local_path)

    # Cleanup
    delete_blog_image(data["url"])
    assert not os.path.exists(local_path)

def test_upload_blog_image_r2(client, mock_admin_auth):
    """Prod mode (USE_R2=True) should upload to R2 with blog/ prefix"""
    mock_upload = MagicMock()
    with patch("routers.blog.USE_R2", True), \
         patch("routers.blog.r2_upload", mock_upload), \
         patch("routers.blog.r2_public_url", return_value="https://assets.zentable.in/blog/test_art.png"):
        res = client.post(
            "/api/blog/upload-image",
            files={"file": ("test_art.png", io.BytesIO(b"png_bytes"), "image/png")}
        )
    assert res.status_code == 200
    data = res.json()
    assert data["success"] is True
    assert "https://assets.zentable.in/blog/" in data["url"]
    mock_upload.assert_called_once()
    assert mock_upload.call_args[0][1].startswith("blog/")

def test_upload_invalid_extension(client, mock_admin_auth):
    """Unsupported extension should return 400"""
    res = client.post(
        "/api/blog/upload-image",
        files={"file": ("bad_script.exe", io.BytesIO(b"evil"), "application/octet-stream")}
    )
    assert res.status_code == 400
    assert "Invalid file format" in res.json()["detail"]

def test_delete_blog_image_cleanup():
    """delete_blog_image should remove from local and call r2_delete"""
    os.makedirs("static/blog", exist_ok=True)
    temp_file = os.path.join("static", "blog", "unit_test_sample.jpg")
    with open(temp_file, "wb") as f:
        f.write(b"data")
    assert os.path.exists(temp_file)

    mock_r2_del = MagicMock()
    with patch("routers.blog.USE_R2", True), patch("routers.blog.r2_delete", mock_r2_del):
        delete_blog_image("/static/blog/unit_test_sample.jpg")

    assert not os.path.exists(temp_file)
    mock_r2_del.assert_called_once_with("blog/unit_test_sample.jpg")
