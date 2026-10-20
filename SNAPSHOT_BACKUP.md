# Complete working-folder backup

This private repository preserves the research Git history and captures current source, protocols and normal tracked research outputs.

## The entire folder

The release **snapshot-2026-10-20-2300** contains `fatigue-ai-research-full-snapshot-2026-10-20.tar.gz`: a complete folder copy, including original `.git`, `.venv`, `.pytest_cache`, every raw dataset and PDF, ignored files, intermediate work, results, and symlinks. No folder content was omitted from that archive.

Capture window: 2026-10-20T20:00:07.806855+00:00 to 2026-10-20T20:00:16.122745+00:00. The ongoing source research directory was not changed or stopped. This is a point-in-work backup, not a claim that unfinished experiments are complete.

The full manifest lists every regular file SHA-256, directory and symlink. The snapshot contains 22333 regular files (3785425543 bytes before compression). The compressed archive is 1528571177 bytes.

The regular Git tree respects the original ignore rules; files too large for normal Git are also in the full release archive. To recover **everything**, download the `.tar.gz` asset, rather than GitHub's automatically generated source-code ZIP.

## Restore

Download the full archive and `SHA256SUMS` from the release, then verify the archive SHA-256 against the matching line. Extract into a new empty directory:

```sh
mkdir recovered-research
tar -xzf fatigue-ai-research-full-snapshot-2026-10-20.tar.gz -C recovered-research
```

The archived Git head before this backup commit was `bb254f3d0a4898ed3daad1056cf7338f18a63ce2`; uncommitted files are preserved in the same archive. The environment and symlink paths are retained exactly; reconstruct a portable Python environment from the requirements if moving to another machine.
