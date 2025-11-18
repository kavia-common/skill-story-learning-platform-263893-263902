#!/bin/bash
cd /home/kavia/workspace/code-generation/skill-story-learning-platform-263893-263902/skill_story_backend
source venv/bin/activate
flake8 .
LINT_EXIT_CODE=$?
if [ $LINT_EXIT_CODE -ne 0 ]; then
  exit 1
fi

