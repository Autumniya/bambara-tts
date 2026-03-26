---
title: Bambara TTS
emoji: 🔊
colorFrom: indigo
colorTo: purple
sdk: docker
app_port: 8000
suggested_hardware: cpu-basic
---

Bambara TTS API built with FastAPI and Coqui-based Bambara voice synthesis.

Main endpoints:
- GET /ping
- POST /synthesize
- POST /batch.zip
- GET /audio/{fname}
