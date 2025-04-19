// ----------------------
// file   : GroupedPage.jsx
// function: 유사한 파일 제목끼리 그룹으로 묶어 보여주는 페이지 + 삭제 기능 포함
// ----------------------

import React, { useEffect, useState } from 'react';
import axios from 'axios';
import { useNavigate } from 'react-router-dom';

// ----------------------
// function: 바이트 단위 → 사람이 읽기 쉬운 형식으로 변환
// return  : "123.4 MB" 형태 문자열
// ----------------------
const formatBytes = (bytes, decimals = 1) => {
  if (!bytes || bytes === 0) return "0 B";
  const k = 1024;
  const dm = decimals < 0 ? 0 : decimals;
  const sizes = ["B", "KB", "MB", "GB", "TB"];
  const i = Math.floor(Math.log(bytes) / Math.log(k));
  return `${parseFloat((bytes / Math.pow(k, i)).toFixed(dm))} ${sizes[i]}`;
};

export default function GroupedPage() {
  const [groups, setGroups] = useState([]);
  const navigate = useNavigate();

  // ----------------------
  // effect: 최초 로딩 시 그룹 목록 조회
  // ----------------------
  useEffect(() => {
    fetchGroups();
  }, []);

  // ----------------------
  // function: 그룹 목록 API 호출
  // ----------------------
  const fetchGroups = async () => {
    try {
      const res = await axios.get('/api/files/grouped');
      setGroups(res.data.groups || []);
    } catch (err) {
      console.error("그룹 파일 조회 실패:", err);
    }
  };

  // ----------------------
  // function: 삭제 요청 처리
  // ----------------------
  const handleDelete = async (fileHash) => {
    if (!window.confirm("정말 삭제하시겠습니까?")) return;
    try {
      await axios.delete(`/api/files/file/hash/${fileHash}`);
      alert("삭제 완료");
      fetchGroups();  // 삭제 후 목록 갱신
    } catch (err) {
      console.error("삭제 실패", err);
      alert("삭제 중 오류 발생");
    }
  };

  return (
    <div className="p-6 space-y-8">
      <h1 className="text-2xl font-bold text-blue-600">유사 파일 그룹 목록</h1>

      {groups.map((group, idx) => (
        <div key={idx} className="space-y-4 border border-gray-300 rounded p-4">
          <h2 className="text-lg font-semibold text-gray-700">Group {idx + 1} ({group.length}개)</h2>

          {group.map((file, index) => (
            <div key={index} className="flex border rounded p-4 gap-4 items-start bg-white">
              <img
                src={file.thumb_path ? `/thumbs/${file.thumb_path}` : "/ui/no-thumb.png"}
                onError={(e) => { e.target.src = "/ui/no-thumb.png"; }}
                alt="thumbnail"
                className="w-36 h-36 object-cover bg-gray-300"
              />
              <div className="flex-1 space-y-2">
                <div className="flex justify-between items-center">
                  <div>
                    <p className="text-xl font-semibold text-gray-800">
                      {file.file_name}
                    </p>
                    <p className="text-sm text-gray-500">{formatBytes(file.file_size)}</p>
                  </div>

                  <div className="flex gap-2">
                    <a
                      href={`/api/files/download/${file.file_hash}`}
                      className="text-sm border border-blue-600 text-blue-600 px-2 py-1 rounded hover:bg-blue-50"
                      download
                    >
                      다운로드
                    </a>
                    <button
                      onClick={() => navigate(`/edit/${file.file_hash}`)}
                      className="text-yellow-600 border border-yellow-600 hover:bg-yellow-100 px-2 py-1 text-sm rounded"
                    >
                      수정
                    </button>
                    <button
                      onClick={() => handleDelete(file.file_hash)}
                      className="text-red-600 border border-red-600 hover:bg-red-100 px-2 py-1 text-sm rounded"
                    >
                      삭제
                    </button>
                  </div>
                </div>

                {file.tags && file.tags.length > 0 ? (
                  <div className="grid grid-cols-4 gap-2">
                    {file.tags.map((tag, i) => (
                      <span key={i} className="border rounded px-2 py-1 text-sm text-center bg-gray-100">
                        {tag}
                      </span>
                    ))}
                  </div>
                ) : (
                  <p className="text-gray-400 text-sm italic">태그 없음</p>
                )}
              </div>
            </div>
          ))}
        </div>
      ))}
    </div>
  );
}
