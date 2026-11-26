---
name: turk-history-documentary
description: Produce sourced, low-cost Turkish history documentary videos with the repository's 20 editorial roles, Remotion, FFmpeg, licensed Wikimedia assets, and strict approval gates.
---

# Turkish History Documentary Production

1. Preserve all 20 role IDs from `config/agents.json`; they are work modules, not 20 paid independent agents.
2. Verify historical claims against official or academic sources and retain source URLs.
3. Default to 60–75 seconds, vertical 1080×1920, 30 fps, and 10–12 distinct scenes.
4. Prefer historical photographs, artifacts, sites, and maps whose Wikimedia Commons license and source page are recorded in the attribution report. Never call a reconstruction an archival image.
5. Use the approved Gemini Charon recording when its script and audio hashes match. A new Charon recording requires explicit confirmation of the unbilled Gemini free tier. Stop if the recording fails or the quota is exhausted.
6. Keep other narrators and paid providers disabled. Use the existing review workflow and require human approval for publication.
7. Keep the AI image provider, faster-whisper audit, PySceneDetect audit, and Instagram Insights disabled by default. Optional audits must run locally on preinstalled models; do not download models without explicit configuration.
8. Remotion renders motion and phrase/word captions; FFmpeg mixes narration/music and produces H.264/AAC. Test with `npm run typecheck` and `python -m unittest discover -s tests -v`.
9. Keep draft artifacts review-only. Verify audio, captions, scene diversity, image licenses, and historical facts; require human approval before publication. Instagram auto-publishing stays disabled.
