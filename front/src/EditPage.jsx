// ----------------------
// file   : EditPage.jsx
// function: 메타데이터 전체 수정 페이지 (파일 이름, 태그, 썸네일 수정)
// ----------------------

import { useParams, useNavigate, useSearchParams } from "react-router-dom";
import { useState, useEffect, useRef } from "react";
import axios from "axios";

export default function EditPage() {
  const { file_hash } = useParams();
  const [searchParams] = useSearchParams();
  const page = searchParams.get("page") || 1;
  const navigate = useNavigate();

  const [fileName, setFileName] = useState("");
  const [tags, setTags] = useState("");
  const [thumb, setThumb] = useState(null);
  const [thumbPreview, setThumbPreview] = useState("");
  const [thumbName, setThumbName] = useState("");

  const inputRef = useRef(null);

  // ----------------------
  // function: 초기 데이터 로딩
  // ----------------------
  useEffect(() => {
    axios.get(`/api/files/file/hash/${file_hash}`).then((res) => {
      setFileName(res.data.file_name);
      setTags(res.data.tags.join(" "));
      setThumbPreview(`/thumbs/${res.data.thumb_path}`);
      setThumbName(res.data.thumb_path);
    });
  }, [file_hash]);

  // ----------------------
  // function: 썸네일 파일 선택 처리
  // ----------------------
  const handleThumbnail = (file) => {
    if (file) {
      setThumb(file);
      setThumbName(file.name);
      const reader = new FileReader();
      reader.onload = () => setThumbPreview(reader.result);
      reader.readAsDataURL(file);
    }
  };

  // ----------------------
  // function: 썸네일 URL을 File 객체로 변환
  // ----------------------
  const fetchImageAsFile = async (url, filename) => {
    const response = await fetch(url);
    const blob = await response.blob();
    return new File([blob], filename, { type: blob.type });
  };

  // ----------------------
  // function: 저장 요청 처리
  // ----------------------
  const handleSubmit = async (e) => {
    e.preventDefault();
    const formData = new FormData();
    formData.append("file_hash", file_hash);
    formData.append("file_name", fileName);

    const validTags = tags
      .split(" ")
      .map((tag) => tag.trim())
      .filter((tag) => tag.length > 0);

    if (validTags.length > 0) {
      validTags.forEach((tag) => formData.append("tags", tag));
    } else {
      formData.append("tags", "");
    }

    if (thumb) {
      formData.append("thumb", thumb);
    }

    await axios.put("/api/files/meta", formData);
    navigate(`/?page=${page}`, { replace: true });
  };

  // ----------------------
  // function: 크롤링 버튼 클릭 시 처리
  // ----------------------
  const handleAutoFill = async () => {
    const match = fileName.match(/RJ\d{4,}/i);
    if (!match) {
      alert("RJ코드를 파일명에서 찾을 수 없습니다");
      return;
    }

    const rjCode = match[0].toUpperCase();

    try {
      const res = await axios.get(`/api/fetch-rj-info?rj_code=${rjCode}`);
      if (!res.data.success) {
        alert("메타데이터를 가져오지 못했습니다");
        return;
      }

      const data = res.data.data;
      //setFileName(`[${rjCode}] ${data.title}`);
      setTags(data.tags.join(" "));
      setThumbPreview(data.thumbnail);
      setThumbName(`${rjCode}.jpg`);

      // ✅ 이미지 URL을 File 객체로 변환하여 thumb에 저장
      const file = await fetchImageAsFile(data.thumbnail, `${rjCode}.jpg`);
      setThumb(file);
    } catch (e) {
      alert("크롤링 중 오류가 발생했습니다");
    }
  };

  return (
    <div className="p-4 max-w-xl mx-auto">
      <h1 className="text-xl mb-4">파일 정보 수정</h1>

      {/* ✅ 자동 채우기 버튼 */}
      <button
        onClick={handleAutoFill}
        className="bg-green-600 text-white px-4 py-2 rounded mb-4"
      >
        RJ코드로 자동 메타 채우기
      </button>

      <form onSubmit={handleSubmit} className="space-y-4">
        {/* 파일 이름 */}
        <div>
          <label className="block mb-1">파일 이름</label>
          <input
            type="text"
            value={fileName}
            onChange={(e) => setFileName(e.target.value)}
            className="w-full border p-2"
          />
        </div>

        {/* 태그 */}
        <div>
          <label className="block mb-1">태그 (스페이스로 구분)</label>
          <input
            type="text"
            value={tags}
            onChange={(e) => setTags(e.target.value)}
            className="w-full border p-2"
          />
        </div>

        {/* 썸네일 업로드 */}
        <div>
          <label className="block mb-1">썸네일</label>
          <div
            onClick={() => inputRef.current.click()}
            onDragOver={(e) => e.preventDefault()}
            onDrop={(e) => {
              e.preventDefault();
              const file = e.dataTransfer.files[0];
              handleThumbnail(file);
            }}
            className="flex items-center justify-center w-full h-32 border-2 border-dashed rounded cursor-pointer bg-white hover:bg-gray-50 text-gray-500 text-sm"
          >
            <span>
              {thumbName
                ? `선택됨: ${thumbName}`
                : "썸네일을 드래그하거나 클릭해서 선택하세요"}
            </span>
          </div>

          <input
            id="thumbInput"
            ref={inputRef}
            type="file"
            accept="image/*"
            onChange={(e) => handleThumbnail(e.target.files[0])}
            className="hidden"
          />

          {thumbPreview && (
            <img
              src={thumbPreview}
              alt="썸네일 미리보기"
              className="w-32 h-32 object-cover mt-2 border rounded"
            />
          )}
        </div>

        <button type="submit" className="bg-blue-600 text-white px-4 py-2 rounded">
          저장
        </button>
      </form>
    </div>
  );
}
