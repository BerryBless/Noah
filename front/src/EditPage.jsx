// ----------------------
// file   : EditPage.jsx
// function: 메타데이터 전체 수정 페이지 (파일 이름, 태그, 썸네일 수정)
// ----------------------

import { useParams, useNavigate } from "react-router-dom";
import { useState, useEffect } from "react";
import axios from "axios";

export default function EditPage() {
  const { file_hash } = useParams();
  const navigate = useNavigate();

  // ----------------------
  // state: 수정 대상 메타데이터
  // ----------------------
  const [fileName, setFileName] = useState("");
  const [tags, setTags] = useState("");
  const [thumb, setThumb] = useState(null);
  const [thumbPreview, setThumbPreview] = useState("");
  const [thumbName, setThumbName] = useState("");

  // ----------------------
  // function: 초기 데이터 로딩
  // return  : file_name, tags, thumbnail_path 세팅
  // ----------------------
  useEffect(() => {
    axios.get(`/api/files/file/hash/${file_hash}`).then((res) => {
      setFileName(res.data.file_name);
      setTags(res.data.tags.join(", "));
      setThumbPreview(`/thumbs/${res.data.thumbnail_path}`);
      setThumbName(res.data.thumbnail_path);
    });
  }, [file_hash]);

  // ----------------------
  // function: 저장 요청 처리
  // return  : 성공 시 목록 페이지로 이동
  // ----------------------
  const handleSubmit = async (e) => {
    e.preventDefault();
    const formData = new FormData();

    formData.append("file_hash", file_hash);
    formData.append("file_name", fileName);

    // ----------------------
    // 유효한 태그만 추출 (빈값, 공백 제거)
    // ----------------------
    const validTags = tags
      .split(",")
      .map((tag) => tag.trim())
      .filter((tag) => tag.length > 0);

    if (validTags.length > 0) {
      validTags.forEach((tag) => formData.append("tags", tag));
    } else {
      // 아예 태그 전송 안 하거나 빈값 전송
      formData.append("tags", ""); // 서버에서 [] 처리
    }

    if (thumb) formData.append("thumb", thumb);

    await axios.put("/api/files/meta", formData);
    navigate("/", { replace: true });
  };

  return (
    <div className="p-4 max-w-xl mx-auto">
      <h1 className="text-xl mb-4">파일 정보 수정</h1>
      <form onSubmit={handleSubmit} className="space-y-4">

        {/* ----------------------
            파일 이름 입력
        ---------------------- */}
        <div>
          <label className="block mb-1">파일 이름</label>
          <input
            type="text"
            value={fileName}
            onChange={(e) => setFileName(e.target.value)}
            className="w-full border p-2"
          />
        </div>

        {/* ----------------------
            태그 입력
        ---------------------- */}
        <div>
          <label className="block mb-1">태그 (쉼표로 구분)</label>
          <input
            type="text"
            value={tags}
            onChange={(e) => setTags(e.target.value)}
            className="w-full border p-2"
          />
        </div>

        {/* ----------------------
            썸네일 업로드 - UploadPage 스타일
        ---------------------- */}
        <div>
          <label className="block mb-1">썸네일</label>

          {/* 업로드 박스 */}
          <label className="flex items-center justify-center w-full h-32 border-2 border-dashed rounded cursor-pointer bg-white hover:bg-gray-50 text-gray-500 text-sm">
            <span>
              {thumbName ? `선택됨: ${thumbName}` : "썸네일을 드래그하거나 클릭해서 선택하세요"}
            </span>
            <input
              type="file"
              accept="image/*"
              onChange={(e) => {
                const file = e.target.files[0];
                if (file) {
                  setThumb(file);
                  setThumbName(file.name);
                  const reader = new FileReader();
                  reader.onload = () => {
                    setThumbPreview(reader.result);
                  };
                  reader.readAsDataURL(file);
                }
              }}
              className="hidden"
            />
          </label>

          {/* 썸네일 미리보기 */}
          {thumbPreview && (
            <img
              src={thumbPreview}
              alt="썸네일 미리보기"
              className="w-32 h-32 object-cover mt-2 border rounded"
            />
          )}
        </div>

        {/* 저장 버튼 */}
        <button type="submit" className="bg-blue-600 text-white px-4 py-2 rounded">
          저장
        </button>
      </form>
    </div>
  );
}
