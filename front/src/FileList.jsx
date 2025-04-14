// ----------------------
// file   : FileList.jsx
// function: 파일 목록 조회 + 검색 + 정렬 + 하이라이트 + 페이지네이션 + 삭제
// ----------------------

import React, { useEffect, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import axios from 'axios';

export default function FileList() {
  // ----------------------
  // state
  // ----------------------
  const [files, setFiles] = useState([]);         // 현재 화면에 표시될 파일 목록
  const [total, setTotal] = useState(0);          // 전체 파일 수 (또는 검색 결과 수)
  const [page, setPage] = useState(1);            // 현재 페이지
  const [size] = useState(10);                    // 페이지당 항목 수
  const [sort, setSort] = useState("created");    // 정렬 방식 ("created", "name")
  const [query, setQuery] = useState("");         // 검색어 (tag: 포함 가능)

  const navigate = useNavigate();

  // ----------------------
  // effect: 페이지, 정렬 변경 시 목록 재조회 또는 재검색
  // ----------------------
  useEffect(() => {
    if (query === "") fetchFiles();
    else handleSearch();
  }, [page, sort]);

  // ----------------------
  // function: 검색어 강조 처리
  // ----------------------
  const highlight = (text, keyword) => {
    if (!keyword) return text;
    const escaped = keyword.replace(/[-/\\^$*+?.()|[\]{}]/g, '\\$&');
    const regex = new RegExp(`(${escaped})`, 'gi');
    return text.split(regex).map((part, i) =>
      regex.test(part) ? <mark key={i} className="bg-yellow-200 text-black rounded px-1">{part}</mark> : part
    );
  };

  // ----------------------
  // function: 전체 목록 조회
  // ----------------------
  const fetchFiles = async () => {
    try {
      const res = await axios.get(`/api/files?page=${page}&size=${size}&sort=${sort}`);
      setFiles(res.data.items || []);
      setTotal(res.data.total || 0);
    } catch (err) {
      console.error('파일 리스트 조회 실패:', err);
    }
  };

  // ----------------------
  // function: 서버에서 검색 결과 조회 (tag: 포함)
  // ----------------------
  const handleSearch = async () => {
    try {
      let url = "";
      if (query.startsWith("tag:")) {
        const tag = query.slice(4).trim();
        url = `/api/files/search?tag=${encodeURIComponent(tag)}&page=${page}&sort=${sort}`;
      } else {
        url = `/api/files/search?keyword=${encodeURIComponent(query)}&page=${page}&sort=${sort}`;
      }

      const res = await axios.get(url);
      setFiles(res.data.items || []);
      setTotal(res.data.total || 0);
    } catch (err) {
      console.error("검색 실패:", err);
    }
  };

  // ----------------------
  // function: 검색 초기화
  // ----------------------
  const clearSearch = () => {
    setQuery("");
    setPage(1);
    fetchFiles(); // 전체 목록 재조회
  };

  // ----------------------
  // function: 파일 삭제 요청
  // ----------------------
  const handleDelete = async (fileHash) => {
    if (!window.confirm("정말 삭제하시겠습니까?")) return;
    try {
      await axios.delete(`/api/files/file/hash/${fileHash}`);
      alert("삭제 완료");

      // 삭제 후 현재 상태에 맞게 재조회
      if (query) handleSearch();
      else fetchFiles();
    } catch (err) {
      console.error("삭제 실패", err);
      alert("삭제 중 오류 발생");
    }
  };

  // ----------------------
  // 계산: 전체 페이지 수
  // ----------------------
  const totalPages = Math.ceil(total / size);

  return (
    <div className="p-4 space-y-6">

      {/* ----------------------
          검색창 + 검색/초기화 버튼
      ---------------------- */}
      <div className="flex gap-2">
        <input
          type="text"
          placeholder='검색어 입력 (예: "tag:게임", "몬스터")'
          value={query}
          onChange={(e) => setQuery(e.target.value)}
          onKeyDown={(e) => {
            if (e.key === 'Enter') {
              setPage(1);
              handleSearch();
            }
          }}
          className="w-full p-2 border rounded text-lg"
        />
        <button
          onClick={() => {
            setPage(1);
            handleSearch();
          }}
          className="px-4 py-2 bg-blue-500 text-white rounded"
        >
          검색
        </button>
        {query && (
          <button
            onClick={clearSearch}
            className="px-4 py-2 bg-gray-300 text-gray-800 rounded"
          >
            초기화
          </button>
        )}
      </div>

      {/* ----------------------
          파일 개수 / 정렬 / 업로드
      ---------------------- */}
      <div className="flex justify-between items-center mb-2">
        <p className="text-blue-500 font-semibold">총 {total}개 파일</p>
        <div className="flex items-center gap-4">
          <select
            value={sort}
            onChange={(e) => {
              setSort(e.target.value);
              setPage(1);
            }}
            className="border rounded px-2 py-1 text-sm text-gray-700"
          >
            <option value="created">최신순</option>
            <option value="name">파일명순</option>
          </select>
          <a
            href="/ui/upload"
            className="text-green-600 font-semibold hover:underline"
          >
            업로드
          </a>
        </div>
      </div>

      {/* ----------------------
          파일 목록 출력
      ---------------------- */}
      {files.length === 0 && (
        <p className="text-gray-500 italic">표시할 파일이 없습니다.</p>
      )}

      {files.map((file, index) => (
        <div key={index} className="flex border rounded p-4 gap-4 items-start">
          {/* 썸네일 */}
          <img
            src={file.thumbnail_path ? `/thumbs/${file.thumbnail_path}` : "/ui/no-thumb.png"}
            onError={(e) => { e.target.src = "/ui/no-thumb.png"; }}
            alt="thumbnail"
            className="w-36 h-36 object-cover bg-gray-300"
          />

          {/* 텍스트 + 태그 + 버튼 */}
          <div className="flex-1 space-y-2">
            <div className="flex justify-between items-center">
              {/* 파일명 + 하이라이트 */}
              <a
                href={`/api/files/download/${file.file_hash}`}
                className="text-xl font-semibold text-blue-600 hover:underline"
                download
              >
                {query && !query.startsWith("tag:")
                  ? highlight(file.file_name, query)
                  : file.file_name}
              </a>

              {/* 수정/삭제 버튼 */}
              <div className="flex gap-2">
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

            {/* 태그 출력 + 하이라이트 */}
            {file.tags && file.tags.length > 0 ? (
              <div className="grid grid-cols-4 gap-2">
                {file.tags.map((tag, i) => (
                  <span key={i} className="border rounded px-2 py-1 text-sm text-center bg-gray-100">
                    {query && query.startsWith("tag:")
                      ? highlight(tag, query.slice(4).trim())
                      : tag}
                  </span>
                ))}
              </div>
            ) : (
              <p className="text-gray-400 text-sm italic">태그 없음</p>
            )}
          </div>
        </div>
      ))}

      {/* ----------------------
          페이지네이션 출력
      ---------------------- */}
      {totalPages > 1 && (
        <div className="flex justify-center gap-2 pt-6 flex-wrap">
          {page > 1 && (
            <button
              onClick={() => setPage(page - 1)}
              className="px-3 py-1 rounded border bg-white text-blue-500"
            >
              이전
            </button>
          )}

          {(() => {
            const pages = [];
            const startPage = Math.max(2, page - 2);
            const endPage = Math.min(totalPages - 1, page + 2);

            pages.push(
              <button
                key={1}
                onClick={() => setPage(1)}
                className={`px-3 py-1 rounded border ${page === 1 ? 'bg-blue-500 text-white' : 'bg-white text-blue-500'}`}
              >
                1
              </button>
            );

            if (startPage > 2) {
              pages.push(<span key="start-ellipsis" className="px-2 py-1 text-gray-500">...</span>);
            }

            for (let i = startPage; i <= endPage; i++) {
              pages.push(
                <button
                  key={i}
                  onClick={() => setPage(i)}
                  className={`px-3 py-1 rounded border ${page === i ? 'bg-blue-500 text-white' : 'bg-white text-blue-500'}`}
                >
                  {i}
                </button>
              );
            }

            if (endPage < totalPages - 1) {
              pages.push(<span key="end-ellipsis" className="px-2 py-1 text-gray-500">...</span>);
            }

            pages.push(
              <button
                key={totalPages}
                onClick={() => setPage(totalPages)}
                className={`px-3 py-1 rounded border ${page === totalPages ? 'bg-blue-500 text-white' : 'bg-white text-blue-500'}`}
              >
                {totalPages}
              </button>
            );

            return pages;
          })()}

          {page < totalPages && (
            <button
              onClick={() => setPage(page + 1)}
              className="px-3 py-1 rounded border bg-white text-blue-500"
            >
              다음
            </button>
          )}
        </div>
      )}
    </div>
  );
}
