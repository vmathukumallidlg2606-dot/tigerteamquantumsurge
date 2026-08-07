# Quantum Surge

An AI-powered study platform for the CompTIA Security+ SY0-701 certification. It combines a Flask web application, local Ollama models, ChromaDB retrieval, DuckDuckGo threat-intelligence search, and optional Firebase-backed user data.

## Quick start

1. Create and activate a Python virtual environment.
2. Install dependencies:

   ```powershell
   pip install -r requirements.txt
   ```

3. Optionally copy `.env.example` to `.env` and configure Firebase Admin credentials. Without Firebase credentials, the application uses local storage.
4. Start Ollama and make sure a supported model is available.
5. Run the application:

   ```powershell
   python server.py
   ```

6. Open `http://127.0.0.1:5000`.

## Testing

```powershell
pytest
```

## Documentation

- [System workflow](QUANTUM_SURGE_WORKFLOW.md)
- [Google authentication setup](GOOGLE_AUTH_SETUP.md)

## Configuration and secrets

Do not commit `.env`, Firebase service-account files, or Cloudflare tunnel credentials. The repository includes `.env.example` and `cloudflared-config.example.yml` as safe starting points.

## License

No license has been selected yet. Add a license before publishing or accepting outside contributions.
