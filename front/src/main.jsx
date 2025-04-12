import React from "react";
import ReactDOM from "react-dom/client";
import { BrowserRouter, Routes, Route } from "react-router-dom";
import FileList from "./FileList";
import UploadPage from "./UploadPage";
import EditPage from "./EditPage"; 

console.log("React 앱 시작됨");

ReactDOM.createRoot(document.getElementById("root")).render(
  <BrowserRouter basename="/ui">
    <Routes>
      <Route path="/" element={<FileList />} />
      <Route path="/upload" element={<UploadPage />} />
      <Route path="/edit/:file_hash" element={<EditPage />} />
    </Routes>
  </BrowserRouter>
);
