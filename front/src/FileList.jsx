import React, { useEffect, useState } from 'react';
import axios from 'axios';

export default function FileList() {
  console.log("🧩 렌더링됨")

  const [files, setFiles] = useState([]);

  useEffect(() => {
    console.log("✅ 파일 목록 불러오는 중...");
    axios.get('/api/files?page=1&size=10')
      .then(res => {
        console.log("📦 파일 수신:", res.data);
        setFiles(res.data.items || []);
      })
      .catch(err => {
        console.error('❌ 파일 리스트 조회 실패:', err);
      });
  }, []);

  return (
    <div className="p-4 space-y-6">
      <input
        type="text"
        placeholder="How to be more confident?"
        className="w-full p-2 border rounded text-lg"
      />

      <p className="text-blue-500 font-semibold">총 {files.length}개 파일</p>

      {files.length === 0 && (
        <p className="text-gray-500 italic">표시할 파일이 없습니다.</p>
      )}

      {files.map((file, index) => {
        console.log("섬네일 경로:", `/thumbs/${file.thumbnail_path}`);  // ✅ 여기에!

        return (
          <div key={index} className="flex border rounded p-4 gap-4">
            <img
              src={
                file.thumbnail_path
                  ? `/thumbs/${file.thumbnail_path}`
                  : "/ui/no-thumb.png"
              }
              onError={(e) => {
                e.target.src = "/ui/no-thumb.png";
              }}
              alt="thumbnail"
              className="w-36 h-36 object-cover bg-gray-300"
            />
            <div className="flex-1">
              <h2 className="text-xl font-semibold">{file.file_name || "이름 없음"}</h2>
              {file.tags && file.tags.length > 0 ? (
                <div className="grid grid-cols-4 gap-2 mt-2">
                  {file.tags.map((tag, i) => (
                    <span
                      key={i}
                      className="border rounded px-2 py-1 text-sm text-center bg-gray-100"
                    >
                      {tag}
                    </span>
                  ))}
                </div>
              ) : (
                <p className="text-gray-400 text-sm italic mt-2">태그 없음</p>
              )}
            </div>
          </div>
        );
      })}

    </div>
  );
}
