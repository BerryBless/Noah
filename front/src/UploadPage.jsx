// ----------------------
// file   : UploadPage.jsx
// function: 썸네일/파일/태그 입력 유지 + WebSocket 업로드 상태 확인 + 각 파일별 업로드 진행률 표시 + 동시 업로드 수 제한 (기본 3개)
// ----------------------

import React, { useState } from "react";
import axios from "axios";
import { useNavigate } from "react-router-dom";
import { limitConcurrency } from "./concurrency"; // 동시 업로드 제한 유틸

export default function UploadPage() {
  const [files, setFiles] = useState([]);
  const [fileNames, setFileNames] = useState([]);
  const [thumb, setThumb] = useState(null);
  const [thumbPreview, setThumbPreview] = useState(null);
  const [tags, setTags] = useState("");
  const [uploadProgressMap, setUploadProgressMap] = useState({});
  const [status, setStatus] = useState("");
  const navigate = useNavigate();

  const isMultiFile = files.length > 1;

  // ----------------------
  // param   : e - 썸네일 파일 선택 이벤트
  // function: 썸네일 파일 및 미리보기 처리
  // ----------------------
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

  // ----------------------
  // param   : e - 파일 선택 이벤트
  // function: 선택된 파일 목록을 상태로 저장
  // ----------------------
  const handleFileSelect = (e) => {
    const selectedFiles = Array.from(e.target.files);
    setFiles(selectedFiles);
    setFileNames(selectedFiles.map(f => f.name));
  };

  // ----------------------
  // param   : e - 제출 이벤트
  // function: 모든 파일을 병렬로 업로드, 동시 3개 제한, 진행률 추적 및 WebSocket 상태 확인
  // ----------------------
  const handleSubmit = async (e) => {
    e.preventDefault();
    if (files.length === 0) return alert("파일을 선택해주세요");

    try {
      const { data } = await axios.get("/get-upload-id");
      const uploadId = data.upload_id;

      if (isMultiFile) {
        // ----------------------
        // 병렬 업로드 (동시 3개 제한)
        // ----------------------
        const uploadTasks = files.map((file) => () => {
          const formData = new FormData();
          formData.append("files", file);
          formData.append("upload_id", uploadId);

          return axios.post("/upload", formData, {
            onUploadProgress: (event) => {
              const percent = Math.round((event.loaded * 100) / event.total);
              setUploadProgressMap((prev) => ({
                ...prev,
                [file.name]: percent,
              }));
            },
          });
        });

        await limitConcurrency(uploadTasks, 3); // 동시에 3개 제한 업로드
        connectWebSocket(uploadId);

      } else {
        // ----------------------
        // 단일 파일 + 태그 + 썸네일
        // ----------------------
        const formData = new FormData();
        formData.append("files", files[0]);
        formData.append("upload_id", uploadId);

        if (thumb) formData.append("thumb", thumb);
        const tagList = tags.split(" ").map(t => t.trim()).filter(t => t);
        tagList.forEach(tag => formData.append("tags", tag));

        await axios.post("/upload", formData, {
          onUploadProgress: (event) => {
            const percent = Math.round((event.loaded * 100) / event.total);
            setUploadProgressMap({
              [files[0].name]: percent,
            });
          },
        });

        connectWebSocket(uploadId);
      }

    } catch (err) {
      console.error("업로드 실패", err);
      alert("업로드 실패: " + (err.response?.data?.detail || err.message));
      setUploadProgressMap({});
    }
  };

  // ----------------------
  // param   : uploadId - 업로드 식별자
  // function: WebSocket을 통해 서버 처리 상태 확인
  // ----------------------
  const connectWebSocket = (uploadId) => {
    const ws = new WebSocket(`ws://localhost:8000/ws/upload/${uploadId}`);

    ws.onmessage = (event) => {
      const data = JSON.parse(event.data);
      setStatus(`상태: ${data.status}`);

      if (["completed", "failed", "duplicate"].includes(data.status)) {
        ws.close();
        setUploadProgressMap({});

        if (data.status === "completed") {
          alert("업로드 완료!");
          navigate("/");
        } else if (data.status === "duplicate") {
          alert("중복된 파일입니다.");
        } else {
          alert("업로드 실패");
        }
      }
    };

    ws.onerror = () => {
      alert("WebSocket 오류");
      setUploadProgressMap({});
    };
  };

  return (
    <div className="p-6 space-y-8">
      <h1 className="text-2xl font-bold">업로드할 파일</h1>
      <form onSubmit={handleSubmit} className="grid grid-cols-1 md:grid-cols-2 gap-10 items-start">

        {/* 썸네일 영역 */}
        {!isMultiFile && (
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
        )}

        {/* 파일 선택 및 업로드 정보 */}
        <div className="flex flex-col gap-4 w-full">
          <div
            onClick={() => document.getElementById("fileInput").click()}
            className="border-2 border-dashed rounded px-4 py-6 text-center cursor-pointer bg-yellow-50"
          >
            {fileNames.length > 0 ? (
              <div className="text-left text-sm text-gray-700">
                <p>업로드할 파일:</p>
                <ul className="list-disc list-inside space-y-2">
                  {fileNames.map((name, idx) => (
                    <li key={idx}>
                      <div className="font-medium">{name}</div>
                      <div className="w-full bg-gray-200 rounded h-2 mt-1">
                        <div
                          className="bg-blue-600 h-2 rounded"
                          style={{ width: `${uploadProgressMap[name] || 0}%` }}
                        />
                      </div>
                      <div className="text-xs text-right text-gray-500 mt-1">
                        {uploadProgressMap[name] || 0}%
                      </div>
                    </li>
                  ))}
                </ul>
              </div>
            ) : (
              <span className="text-gray-500 text-sm">파일을 드래그하거나 클릭해서 선택하세요</span>
            )}
            <input
              type="file"
              onChange={handleFileSelect}
              className="hidden"
              id="fileInput"
              multiple
            />
          </div>

          {/* 태그 입력 또는 다중파일 안내 */}
          {isMultiFile ? (
            <div className="text-sm text-gray-600 bg-yellow-100 border border-yellow-300 p-2 rounded">
              여러 파일이 감지되었습니다. 태그 및 썸네일 입력은 비활성화됩니다.
            </div>
          ) : (
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
          )}

          {/* 업로드 상태 */}
          {status && (
            <div className="text-sm text-gray-700">현재 상태: {status}</div>
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