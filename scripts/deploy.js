const { ethers } = require('hardhat');

async function main() {
  const [deployer] = await ethers.getSigners();
  console.log('Deploying from:', deployer.address);
  console.log('Balance:', ethers.formatEther(await ethers.provider.getBalance(deployer.address)), 'ETH');

  const PQCAnchor = await ethers.getContractFactory('PQCAnchor');
  const contract  = await PQCAnchor.deploy();
  await contract.waitForDeployment();

  const addr = await contract.getAddress();
  console.log('PQCAnchor deployed at:', addr);

  // Save address for Python scripts
  const fs = require('fs');
  fs.writeFileSync('./python/contract_address.txt', addr);
  console.log('Contract address saved to python/contract_address.txt');
}

main().catch(e => { console.error(e); process.exit(1); });
