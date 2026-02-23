require('@nomicfoundation/hardhat-toolbox');

module.exports = {
  solidity: {
    version: '0.8.19',
    settings: {
      optimizer: { enabled: true, runs: 200 }
    }
  },
  networks: {
    hardhat: {
      chainId: 31337,
      mining: {
        auto: true,           // mine a block per transaction
        interval: 0           // instant mining for simulation
      }
    },
    localhost: {
      url: 'http://127.0.0.1:8545',
      chainId: 31337
    }
  }
};
