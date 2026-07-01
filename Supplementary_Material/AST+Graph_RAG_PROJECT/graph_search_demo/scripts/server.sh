PYTHONPATH=src \
    gunicorn \
    --bind "0.0.0.0:${http_port:-5001}" \
    --workers "${thread_workers:-1}" \
    --timeout 500 \
    --preload \
    app:app