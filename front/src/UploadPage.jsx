import React, { useState } from "react";
import axios from "axios";
import { useNavigate } from "react-router-dom";

export default function UploadPage() {
  const [file, setFile] = useState(null);
  const [fileName, setFileName] = useState("");
  const [thumb, setThumb] = useState(null);
  const [thumbPreview, setThumbPreview] = useState(null);
  const [tags, setTags] = useState("");
  const [dragOver, setDragOver] = useState(false);
  const [thumbDragOver, setThumbDragOver] = useState(false);
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

  const handleThumbDrop = (e) => {
    e.preventDefault();
    setThumbDragOver(false);
    const dropped = e.dataTransfer.files[0];
    if (dropped && dropped.type.startsWith("image/")) {
      setThumb(dropped);
      const reader = new FileReader();
      reader.onloadend = () => setThumbPreview(reader.result);
      reader.readAsDataURL(dropped);
    }
  };

  const handleFileDrop = (e) => {
    e.preventDefault();
    setDragOver(false);
    const droppedFile = e.dataTransfer.files[0];
    if (droppedFile) {
      setFile(droppedFile);
      setFileName(droppedFile.name);
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

    const tagList = tags
      .split(" ")
      .map((tag) => tag.trim())
      .filter((t) => t);
    tagList.forEach((tag) => formData.append("tags", tag));

    try {
      const res = await axios.post("/api/upload/file", formData);
      alert("업로드 완료: " + res.data.message);
      window.location.href = "/ui/";
    } catch (err) {
      console.error("업로드 실패", err);
      alert("업로드 실패: " + err.response?.data?.detail || err.message);
    }
  };

  return (
    <div className="p-6 space-y-8">
      <h1 className="text-2xl font-bold">업로드할 파일</h1>
      <form onSubmit={handleSubmit} className="grid grid-cols-1 md:grid-cols-2 gap-10 items-start">
        {/* 썸네일 */}
        <div
          onClick={() => document.getElementById("thumbInput").click()}
          onDrop={handleThumbDrop}
          onDragOver={(e) => {
            e.preventDefault();
            setThumbDragOver(true);
          }}
          onDragLeave={() => setThumbDragOver(false)}
          className={`w-full h-40 border-2 border-dashed flex items-center justify-center rounded cursor-pointer transition-colors ${thumbDragOver ? "bg-yellow-100 border-yellow-500" : "bg-yellow-300"}`}
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

        {/* 우측 입력란 */}
        <div className="flex flex-col gap-4 w-full">
          <div
            onClick={() => document.getElementById("fileInput").click()}
            onDrop={handleFileDrop}
            onDragOver={(e) => {
              e.preventDefault();
              setDragOver(true);
            }}
            onDragLeave={() => setDragOver(false)}
            className={`border-2 border-dashed rounded px-4 py-6 text-center cursor-pointer transition-colors ${dragOver ? "bg-yellow-100 border-yellow-500" : "bg-yellow-50"}`}
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
              <span className="text-gray-500 text-sm">ZIP 파일을 여기에 드래그하거나 클릭하세요</span>
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
