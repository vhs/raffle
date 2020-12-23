#!/bin/bash

set -e

RAFFLE_FILE=$1

source ${RAFFLE_FILE}

RAFFLE_TIME=${RAFFLE_TIME:?"timestamp for raffle"}
RAFFLE_NAME=${RAFFLE_NAME:?"string name of the raffle"}
RAFFLE_COUNT=${RAFFLE_COUNT:?"number of distributions for this raffle"}
RAFFLE_DICE=${RAFFLE_DICE:?"an unpredictable time-forward string but past immutable (trump tweet?)"}
RAFFLE_SALT=${RAFFLE_SALT:?"an unpredictable time-forward string but past immutable (latest bitcoin block hash?)"}
ENTRANTS=${ENTRANTS:?"distinct list of entrants by external identity (ie email addresses)"}

function hash {
  echo -n $(echo -n "$*" | openssl dgst -binary -sha256 | xxd -c 32 -p)
}

# credit to colinhb https://stackoverflow.com/a/55986217
function hexintsplit() {
  echo "${1}" |
    fold -w 16 |
    sed 's/^/0x/' |
    nl
  echo "${2}" |
    fold -w 16 |
    sed 's/^/0x/' |
    nl
}

function xor() {
  hexintsplit $* |
  sort -n |
  cut -f 2 |
  paste - - |
  while read -r a b; do
    printf "%#0${#a}x" "$(( a ^ b ))"
  done |
  sed 's/0x//g' |
  paste -s -d '\0' -
}

function compare() {
  hexintsplit $* |
  sort -n |
  cut -f 2 |
  paste - - |
  while read -r a b; do
    if (( a < b )); then
      echo -n -1;
      return;
    fi
    if (( a > b )); then
      echo -n 1;
      return;
    fi
  done

  echo -n 0;
  return;
}

function hexsort() {
  local -n arr=$1

  len=${#arr[@]}
  i=1

  while (( i < len ))
  do
    x=${arr[${i}]}
    j=$(( i - 1 ))
    dist=$(compare ${arr[${j}]} ${x})
    while (( j >= 0 )) && (( dist > 0 ))
    do
      arr[$(( j + 1 ))]=${arr[${j}]}
      j=$(( j - 1 ))
    done
    arr[$(( j + 1 ))]=${x}
    i=$(( i + 1 ))
  done
}

# hash key for this raffle
KEY=$(hash ${RAFFLE_TIME} ${RAFFLE_NAME} ${RAFFLE_COUNT})
# the dice hash for this raffle
DICE=$(hash ${RAFFLE_DICE} ${RAFFLE_SALT})
# the roll result of this raffle
ROLL=$(hash ${KEY} ${DICE})
# hashes of entrants for this raffle
declare -A ENTRIES
declare -A DISTRIBUTIONS
ENTRY_PICK_LIST=()

while read -r entry
do
  ENTRANT_HASH=$(hash ${entry} ${DICE})
  ENTRANT_KEY=$(xor ${ENTRANT_HASH} ${ROLL})

  ENTRIES["${ENTRANT_KEY}"]="${entry}"
  DISTRIBUTIONS["${ENTRANT_KEY}"]=0

  ENTRY_PICK_LIST+=("${ENTRANT_KEY}")
done <<< "${ENTRANTS}"

hexsort ENTRY_PICK_LIST

index=0
distributed=0
count=${#ENTRY_PICK_LIST[@]}

while (( distributed < ${RAFFLE_COUNT} ))
do
  if (( index >= count ))
  then
    index=0
  fi

  WINNER_KEY=${ENTRY_PICK_LIST[${index}]}
  WINNER_ACCUMULATED_DISTRIBUTIONS=DISTRIBUTIONS[${WINNER_KEY}]
  DISTRIBUTIONS[${WINNER_KEY}]=$(( WINNER_ACCUMULATED_DISTRIBUTIONS + 1 ))

  distributed=$(( distributed + 1 ))
  index=$(( index + 1))
done

declare -A RESULTS

for key in "${ENTRY_PICK_LIST[@]}"
do
  ENTRANT=${ENTRIES[${key}]}
  WINS=${DISTRIBUTIONS[${key}]}

  RESULTS[${ENTRANT}]=${WINS}

  echo "${ENTRANT} wins ${WINS}"
done

RESULTS_FILE="${RAFFLE_FILE}.results"

touch -d "${RAFFLE_TIME}" ${RESULTS_FILE}

echo "RAFFLE_TIME=\"${RAFFLE_TIME}\"" >> ${RESULTS_FILE}
echo "RAFFLE_NAME=\"${RAFFLE_NAME}\"" >> ${RESULTS_FILE}
echo "RAFFLE_COUNT=\"${RAFFLE_COUNT}\"" >> ${RESULTS_FILE}
echo "RAFFLE_DICE=\"${RAFFLE_DICE}\"" >> ${RESULTS_FILE}
echo "RAFFLE_SALT=\"${RAFFLE_SALT}\"" >> ${RESULTS_FILE}
echo "ENTRANTS=\"${ENTRANTS}\"" >> ${RESULTS_FILE}

echo "KEY=\"${KEY}\"" >> ${RESULTS_FILE}
echo "DICE=\"${DICE}\"" >> ${RESULTS_FILE}
echo "ROLL=\"${ROLL}\"" >> ${RESULTS_FILE}

for key in "${!ENTRY_PICK_LIST[@]}"; do
  echo "${key}=\"${ENTRY_PICK_LIST[$key]}\"" >> ${RESULTS_FILE}
done

for key in "${!ENTRIES[@]}"; do
  echo "${key}=\"${ENTRIES[$key]}\"" >> ${RESULTS_FILE}
done

for key in "${!DISTRIBUTIONS[@]}"; do
  echo "${key}=\"${DISTRIBUTIONS[$key]}\"" >> ${RESULTS_FILE}
done

for key in "${!RESULTS[@]}"; do
  echo "${key}=\"${RESULTS[$key]}\"" >> ${RESULTS_FILE}
done
