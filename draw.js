#!/usr/bin/node

const fs = require("fs");
const crypto = require("crypto");
const hash = (input) => crypto.createHash("sha256").update(input).digest("hex");

const raffleFile = process.argv[2];
const raffle = require(raffleFile);

(function validate() {
    if (!raffle.time) throw "timestamp for raffle";
    if (!raffle.name) throw "string name of the raffle";
    if (!raffle.count) throw "number of distributions for this raffle";
    if (!raffle.dice) throw "an unpredictable time-forward string but past immutable (trump tweet?)";
    if (!raffle.salt) throw "an unpredictable time-forward string but past immutable (latest bitcoin block hash?)";
    if (!raffle.entrants) throw "distinct list of entrants by external identity (ie email addresses)";
})();

const key = hash(`${raffle.time} ${raffle.name} ${raffle.count.toString()}`);
const dice = hash(`${raffle.dice} ${raffle.salt}`);
const roll = hash(`${key} ${dice}`);

const entries = new Map();
const distributions = new Map();
const entryPickList = [];

for (const entry of raffle.entrants) {
    const entrantHash = hash(`${entry} ${dice}`);
    const entrantKey = (BigInt(`0x${entrantHash}`) ^ BigInt(`0x${roll}`)).toString(16);

    entries.set(entrantKey, entry);
    distributions.set(entrantKey, 0);

    entryPickList.push(entrantKey);
}

entryPickList.sort((a, b) => {
    const aI = BigInt(`0x${a}`);
    const bI = BigInt(`0x${b}`);

    if (aI < bI) return -1;
    if (aI > bI) return 1;

    return 0;
});

let index = 0;
for (let distributed = 0; distributed < raffle.count; distributed++) {
    if (index >= entryPickList.length) {
        index = 0;
    }

    const winnerKey = entryPickList[index];
    distributions.set(winnerKey, distributions.get(winnerKey) + 1);

    index += 1;
}

const results = new Map();

for (const key of entryPickList) {
    const entrant = entries.get(key);
    const wins = distributions.get(key);

    results.set(entrant, wins);

    console.log(`${entrant} wins ${wins}`);
}

const resultsFile = `${raffleFile}.results.json`;

const output = {
    raffle: raffle,
    key: key,
    dice: dice,
    roll: roll,
    entryPickList: entryPickList,
    entries: Array.from(entries.entries()),
    distributions: Array.from(distributions.entries()),
    results: Array.from(results.entries())
};

fs.writeFileSync(resultsFile, JSON.stringify(output));
