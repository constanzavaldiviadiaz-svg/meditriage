import http from 'k6/http';
import { check } from 'k6';

export const options = {
  stages: [
    { duration: '30s', target: 30 },
    { duration: '90s', target: 60 },
    { duration: '30s', target: 0 },
  ],
};

export default function () {
  const res = http.get('http://localhost:8088/health');
  check(res, {
    'status es 200': (r) => r.status === 200,
  });
}
