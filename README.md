<p align="center">
  <img src="https://github-readme-stats.vercel.app/api?username=daoch4n&show_icons=true&theme=radical" alt="👀" />
  <img src="https://github-readme-streak-stats.herokuapp.com/?user=daoch4n&theme=radical" alt="👀" />
</p>

# Open LLM VTuber

Talk to any LLM with hands-free voice interaction, voice interruption, and Live2D avatar running locally across platforms.

## Building the Frontend

The frontend is built using Vite and React. To build the frontend, run:

```bash
./build_frontend.sh
```

This will:
1. Install dependencies in the `frontend-src` directory
2. Build the frontend to `frontend-src/dist/web`
3. The server will automatically serve files from this location

## Running the Server

To run the server:

```bash
python run_server.py
```

The server will serve the frontend directly from the `frontend-src/dist/web` directory.

## Emotion-Based Pose Changes

The Shizuku Live2D model supports emotion-based pose changes. When the AI responds with emotion tags like `[joy:0.7]` or `[surprise:0.3]`, the model will automatically change its facial expression and body pose to match the emotion.
