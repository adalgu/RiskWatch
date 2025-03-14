#!/bin/bash

while IFS= read -r line || [ -n "$line" ]; do
  # 빈 줄이나 주석(#)으로 시작하는 줄은 건너뜁니다.
  if [[ -z "$line" || "$line" =~ ^# ]]; then
    continue
  fi
  
  # '='가 포함되어 있지 않으면 건너뜁니다.
  if [[ "$line" != *"="* ]]; then
    echo "Skipping improperly formatted line: $line"
    continue
  fi
  
  # 한 번에 하나의 비밀을 등록합니다.
  infisical secrets set "$line"
  echo "Registered: $line"
done < .env