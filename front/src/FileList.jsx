// ----------------------
// file   : FileList.jsx
// function: 파일 목록 조회 + 검색 + 정렬 + 하이라이트 + 페이지네이션 + 삭제 + RJ코드 일괄 크롤링
// ----------------------

import React, { useEffect, useState } from 'react';
import { useNavigate, useSearchParams, useLocation } from 'react-router-dom';
import axios from 'axios';

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

export default function FileList() {
  // ----------------------
  // state
  // ----------------------
  const [files, setFiles] = useState([]);         // 현재 화면에 표시될 파일 목록
  const [total, setTotal] = useState(0);          // 전체 파일 수
  const [size] = useState(10);                    // 페이지당 항목 수
  const [sort, setSort] = useState("created");    // 정렬 기준
  const [query, setQuery] = useState("");         // 검색어
  const [searchParams] = useSearchParams();       // 쿼리스트링 파싱
  const location = useLocation();                 // URL 변경 감지
  const navigate = useNavigate();

  // ----------------------
  // 계산된 현재 페이지 번호
  // ----------------------
  const page = Number(searchParams.get("page")) || 1;

  // ----------------------
  // effect: URL 변경 or 정렬 기준 변경 시 목록 조회
  // ----------------------
  useEffect(() => {
    if (query === "") fetchFiles();
    else handleSearch();
  }, [location.search, sort]);

  // ----------------------
  // function: 검색어 강조 표시
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
  // function: 검색 수행 (태그 또는 키워드)
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
    navigate("/?page=1");
  };

  // ----------------------
  // function: 페이지 이동
  // ----------------------
  const handlePageChange = (targetPage) => {
    navigate(`/?page=${targetPage}`);
  };

  // ----------------------
  // function: 파일 삭제 요청
  // ----------------------
  const handleDelete = async (fileHash) => {
    if (!window.confirm("정말 삭제하시겠습니까?")) return;
    try {
      await axios.delete(`/api/files/file/hash/${fileHash}`);
      alert("삭제 완료");

      if (query) handleSearch();
      else fetchFiles();
    } catch (err) {
      console.error("삭제 실패", err);
      alert("삭제 중 오류 발생");
    }
  };

  // ----------------------
  // function: RJ코드 크롤링 (태그 없는 파일만 자동 업데이트)
  // ----------------------
  const handleBulkCrawl = async () => {
    if (!window.confirm("RJ코드 포함 + 태그 없는 파일을 자동 보정하시겠습니까?")) return;

    const rjRegex = /RJ\d{4,}/i;

    for (const file of files) {
      if (!file.file_name.match(rjRegex)) continue;
      if (!file.tags || file.tags.length > 0) continue;

      const rjCode = file.file_name.match(rjRegex)[0].toUpperCase();
      try {
        const res = await axios.get(`/api/fetch-rj-info?rj_code=${rjCode}`);
        if (!res.data.success) {
          console.warn(`[SKIP] ${file.file_name}: 크롤링 실패`);
          continue;
        }

        const data = res.data.data;
        const formData = new FormData();
        formData.append("file_hash", file.file_hash);
        formData.append("file_name", file.file_name);  // ✅ 제목은 기존 유지
        data.tags.forEach(tag => formData.append("tags", tag));

        // 썸네일 이미지 다운로드 후 FormData에 첨부
        const imgRes = await fetch(data.thumbnail);
        const blob = await imgRes.blob();
        const thumbFile = new File([blob], `${rjCode}.jpg`, { type: blob.type });
        formData.append("thumb", thumbFile);

        await axios.put("/api/files/meta", formData);
        console.log(`[OK] ${rjCode} 업데이트 완료`);
      } catch (e) {
        console.error(`[ERROR] ${file.file_name}`, e);
      }
    }

    alert("자동 크롤링 완료. 목록을 새로고침합니다.");
    fetchFiles();
  };

  // ----------------------
  // 계산: 전체 페이지 수
  // ----------------------
  const totalPages = Math.ceil(total / size);

  return (
    <div className="p-4 space-y-6">

      {/* 검색창 */}
      <div className="flex gap-2">
        <input
          type="text"
          placeholder='검색어 입력 (예: "tag:게임", "몬스터")'
          value={query}
          onChange={(e) => setQuery(e.target.value)}
          onKeyDown={(e) => {
            if (e.key === 'Enter') navigate("/?page=1");
          }}
          className="w-full p-2 border rounded text-lg"
        />
        <button
          onClick={() => navigate("/?page=1")}
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

      {/* 정렬 + 업로드 + 크롤링 */}
      <div className="flex justify-between items-center mb-2">
        <p className="text-blue-500 font-semibold">총 {total}개 파일</p>
        <div className="flex items-center gap-4">
          <select
            value={sort}
            onChange={(e) => {
              setSort(e.target.value);
              navigate("/?page=1");
            }}
            className="border rounded px-2 py-1 text-sm text-gray-700"
          >
            <option value="created">최신순</option>
            <option value="name">파일명순</option>
          </select>
          <a href="/ui/upload" className="text-green-600 font-semibold hover:underline">업로드</a>
          <button
            onClick={handleBulkCrawl}
            className="px-4 py-2 bg-red-600 text-white rounded"
          >
            RJ코드 크롤링
          </button>
          <button
            onClick={() => navigate("/grouped")}
            className="px-4 py-2 bg-purple-600 text-white rounded"
          >
            그룹별로 묶기
          </button>
        </div>
      </div>

      {/* 파일 목록 및 페이지네이션은 동일 */}
      {/* 파일 목록 */}
      {files.length === 0 ? (
        <p className="text-gray-500 italic">표시할 파일이 없습니다.</p>
      ) : (
        files.map((file, index) => (
          <div key={index} className="flex border rounded p-4 gap-4 items-start">
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
                    onClick={() => navigate(`/edit/${file.file_hash}?page=${page}`)}
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
                      {query.startsWith("tag:")
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
        ))
      )}

      {/* 페이지네이션 */}
      {totalPages > 1 && (
        <div className="flex justify-center gap-2 pt-6 flex-wrap">
          {page > 1 && (
            <button onClick={() => handlePageChange(page - 1)} className="px-3 py-1 rounded border bg-white text-blue-500">
              이전
            </button>
          )}

          {(() => {
            const pages = [];
            const start = Math.max(2, page - 2);
            const end = Math.min(totalPages - 1, page + 2);

            pages.push(
              <button
                key={1}
                onClick={() => handlePageChange(1)}
                className={`px-3 py-1 rounded border ${page === 1 ? 'bg-blue-500 text-white' : 'bg-white text-blue-500'}`}
              >
                1
              </button>
            );

            if (start > 2) {
              pages.push(<span key="start-ellipsis" className="px-2 py-1 text-gray-500">...</span>);
            }

            for (let i = start; i <= end; i++) {
              pages.push(
                <button
                  key={i}
                  onClick={() => handlePageChange(i)}
                  className={`px-3 py-1 rounded border ${page === i ? 'bg-blue-500 text-white' : 'bg-white text-blue-500'}`}
                >
                  {i}
                </button>
              );
            }

            if (end < totalPages - 1) {
              pages.push(<span key="end-ellipsis" className="px-2 py-1 text-gray-500">...</span>);
            }

            pages.push(
              <button
                key={totalPages}
                onClick={() => handlePageChange(totalPages)}
                className={`px-3 py-1 rounded border ${page === totalPages ? 'bg-blue-500 text-white' : 'bg-white text-blue-500'}`}
              >
                {totalPages}
              </button>
            );

            return pages;
          })()}

          {page < totalPages && (
            <button onClick={() => handlePageChange(page + 1)} className="px-3 py-1 rounded border bg-white text-blue-500">
              다음
            </button>
          )}
        </div>
      )}
    </div>
  );
}
