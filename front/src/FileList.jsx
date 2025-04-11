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

  const handleDelete = async (fileHash) => {
    if (!window.confirm("정말 삭제하시겠습니까?")) return;
    try {
      await axios.delete(`/api/files/file/hash/${fileHash}`);
      alert("삭제 완료");
      setFiles(files.filter(f => f.file_hash !== fileHash));
    } catch (err) {
      console.error("❌ 삭제 실패", err);
      alert("삭제 중 오류 발생");
    }
  };

  return (
    <div className="p-4 space-y-6">
      <input
        type="text"
        placeholder="How to be more confident?"
        className="w-full p-2 border rounded text-lg"
      />

      <div className="flex justify-between items-center mb-2">
        <p className="text-blue-500 font-semibold">총 {files.length}개 파일</p>
        <a
          href="/ui/upload"
          className="text-green-600 font-semibold hover:underline"
        >
          업로드
        </a>
      </div>
      {files.length === 0 && (
        <p className="text-gray-500 italic">표시할 파일이 없습니다.</p>
      )}

      {files.map((file, index) => {
        console.log("섬네일 경로:", `/thumbs/${file.thumbnail_path}`);

        return (
          <div key={index} className="flex border rounded p-4 gap-4 items-start">
            {/* 썸네일 */}
            <img
              src={file.thumbnail_path ? `/thumbs/${file.thumbnail_path}` : "/ui/no-thumb.png"}
              onError={(e) => { e.target.src = "/ui/no-thumb.png"; }}
              alt="thumbnail"
              className="w-36 h-36 object-cover bg-gray-300"
            />

            {/* 텍스트 + 태그 + 삭제버튼 포함 영역 */}
            <div className="flex-1 space-y-2">
              <div className="flex justify-between items-center">
                <a
                  href={`/api/files/download/${file.file_hash}`}
                  className="text-xl font-semibold text-blue-600 hover:underline"
                  download
                >
                  {file.file_name}
                </a>
                <button
                  onClick={() => handleDelete(file.file_hash)}
                  className="text-red-600 border border-red-600 hover:bg-red-100 px-2 py-1 text-sm rounded"
                >
                  삭제
                </button>
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
        );
      })}
    </div>
  );
}
