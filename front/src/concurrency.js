// ----------------------
// file   : front/src/utils/concurrency.js
// function: 동시 실행 수 제한된 비동기 작업 실행 유틸리티
// ----------------------

/**
 * 동시 실행 제한 Promise 실행기
 * 
 * @param {Function[]} tasks - Promise를 반환하는 함수 배열
 * @param {number} limit - 동시에 실행할 최대 작업 수
 * @returns {Promise<*>[]} - 모든 작업의 Promise 결과
 */
export async function limitConcurrency(tasks, limit) {
    const results = [];
    const executing = [];
  
    for (const task of tasks) {
      const p = task();
      results.push(p);
  
      const e = p.then(() => {
        executing.splice(executing.indexOf(e), 1);
      });
      executing.push(e);
  
      if (executing.length >= limit) {
        await Promise.race(executing);
      }
    }
  
    return Promise.all(results);
  }
  