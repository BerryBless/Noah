import React, { useState } from "react";
import axios from "axios";
import { useNavigate } from "react-router-dom";

export default function UploadPage() {
  const [file, setFile] = useState(null);
  const [fileName, setFileName] = useState("");
  const [thumb, setThumb] = useState(null);
  const [thumbPreview, setThumbPreview] = useState(null);
  const [tags, setTags] = useState("");
  const [uploadProgress, setUploadProgress] = useState(0);
  const navigate = useNavigate();

  const handleThumbChange = (e) => {
    const file = e.target.files[0];
    setThumb(file);
    if (file) {
      const reader = new FileReader();
      reader.onloadend = () => setThumbPreview(reader.result);
      reader.readAsDataURL(file);
    } else {
      setThumbPreview(null);
    }
  };

  const handleFileSelect = (e) => {
    const selectedFile = e.target.files[0];
    if (selectedFile) {
      setFile(selectedFile);
      setFileName(selectedFile.name);
    }
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    if (!file) return alert("파일을 선택해주세요");

    const formData = new FormData();
    formData.append("file", file, fileName);
    if (thumb) formData.append("thumb", thumb);
    const tagList = tags.split(" ").map((t) => t.trim()).filter((t) => t);
    tagList.forEach((tag) => formData.append("tags", tag));
    // upload_id 추가!
    const { data } = await axios.get("/get-upload-id");
    formData.append("upload_id", data.upload_id);
    try {
      const res = await axios.post("/upload", formData, {
        onUploadProgress: (progressEvent) => {
          const percent = Math.round((progressEvent.loaded * 100) / progressEvent.total);
          setUploadProgress(percent);
        },
      });
      alert("업로드 완료: " + res.data.message);
      setUploadProgress(0);
      window.location.href = "/ui/";
    } catch (err) {
      console.error("업로드 실패", err);
      alert("업로드 실패: " + err.response?.data?.detail || err.message);
      setUploadProgress(0);
    }
  };

  return (
    <div className="p-6 space-y-8">
      <h1 className="text-2xl font-bold">업로드할 파일</h1>
      <form onSubmit={handleSubmit} className="grid grid-cols-1 md:grid-cols-2 gap-10 items-start">
        {/* 썸네일 업로드 */}
        <div
          onClick={() => document.getElementById("thumbInput").click()}
          className="w-full h-40 border-2 border-dashed flex items-center justify-center rounded cursor-pointer bg-yellow-300"
        >
          {thumbPreview ? (
            <img src={thumbPreview} alt="thumb preview" className="object-cover w-full h-full rounded" />
          ) : (
            <span className="text-center text-sm text-gray-700">썸네일 업로드<br />파일 입력되면 미리보기</span>
          )}
          <input
            type="file"
            id="thumbInput"
            accept="image/*"
            onChange={handleThumbChange}
            className="hidden"
          />
        </div>

        {/* 파일 업로드 */}
        <div className="flex flex-col gap-4 w-full">
          <div
            onClick={() => document.getElementById("fileInput").click()}
            className="border-2 border-dashed rounded px-4 py-6 text-center cursor-pointer bg-yellow-50"
          >
            {fileName ? (
              <div>
                <p className="text-sm text-gray-700">업로드할 파일: {fileName}</p>
                <input
                  type="text"
                  value={fileName}
                  onChange={(e) => setFileName(e.target.value)}
                  className="mt-2 border rounded px-2 py-1 w-full text-sm"
                />
              </div>
            ) : (
              <span className="text-gray-500 text-sm">파일을 드래그하거나 클릭해서 선택하세요</span>
            )}
            <input
              type="file"
              onChange={handleFileSelect}
              className="hidden"
              id="fileInput"
            />
          </div>

          <div>
            <label className="block text-sm font-medium mb-1">태그 (스페이스로 구분)</label>
            <input
              type="text"
              value={tags}
              onChange={(e) => setTags(e.target.value)}
              placeholder="예: 게임 이미지 몬헌"
              className="border rounded px-2 py-1 w-full"
            />
          </div>

          {uploadProgress > 0 && (
            <div className="w-full bg-gray-200 rounded">
              <div
                className="bg-blue-600 text-white text-xs p-1 text-center rounded"
                style={{ width: `${uploadProgress}%` }}
              >
                {uploadProgress}%
              </div>
            </div>
          )}

          <button
            type="submit"
            className="bg-blue-600 text-white px-4 py-2 rounded hover:bg-blue-700 self-start"
          >
            업로드
          </button>
        </div>
      </form>
    </div>
  );
}
