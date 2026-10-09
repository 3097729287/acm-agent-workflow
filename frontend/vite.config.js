import { readFileSync } from 'node:fs';
import { defineConfig } from 'vite';
import react from '@vitejs/plugin-react';
export default defineConfig({ plugins: [react()], define: { __TB_VERSION__: JSON.stringify(readFileSync(new URL('../VERSION', import.meta.url), 'utf8').trim()) }, server: { proxy: { '/api': { target: process.env.TB_API_URL || 'http://127.0.0.1:18765', changeOrigin: true, configure(proxy) { proxy.on('proxyReq', (request) => { request.removeHeader('origin'); request.removeHeader('sec-fetch-site'); }); } } } }, build: { target: 'es2022' } });
