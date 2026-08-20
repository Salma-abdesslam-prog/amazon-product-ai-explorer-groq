#!/bin/bash
set -e

echo "========================================="
echo "   Amazone-Product-AI-Explorer — Starting"
echo "========================================="

if [ -z "$GROQ_API_KEY" ] && [ ! -f ".streamlit/secrets.toml" ]; then
  echo ""
  echo "WARNING: No GROQ_API_KEY found (env var or .streamlit/secrets.toml)."
  echo "  Get a free key at https://console.groq.com/keys"
  echo "  Then either:"
  echo "    export GROQ_API_KEY=gsk_..."
  echo "  or copy .streamlit/secrets.toml.example to .streamlit/secrets.toml"
  echo "  and fill it in. The app will still start, but chat will be disabled."
  echo ""
fi

echo "Starting Streamlit app on http://localhost:8501 ..."
streamlit run streamlit_app.py
