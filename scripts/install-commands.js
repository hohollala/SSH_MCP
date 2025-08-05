#!/usr/bin/env node

/**
 * SSH MCP 명령어 문서 설치 스크립트
 * 
 * 사용법:
 *   node scripts/install-commands.js          # 설치
 *   node scripts/install-commands.js --force  # 강제 설치 (기존 파일 덮어쓰기)
 *   node scripts/install-commands.js --info   # 설치 정보 조회
 *   node scripts/install-commands.js --uninstall # 제거
 */

import { CommandInstaller } from '../dist/command-installer.js';
import { createLogger } from '../dist/logger.js';

const logger = createLogger('InstallScript');

async function main() {
  const args = process.argv.slice(2);
  const force = args.includes('--force');
  const info = args.includes('--info');
  const uninstall = args.includes('--uninstall');
  const help = args.includes('--help') || args.includes('-h');

  if (help) {
    console.log(`
SSH MCP Commands Installation Script

Usage:
  node scripts/install-commands.js [options]

Options:
  --force      Force installation (overwrite existing files)
  --info       Show installation information
  --uninstall  Remove all command documentation files
  --help, -h   Show this help message

Examples:
  node scripts/install-commands.js          # Install command docs
  node scripts/install-commands.js --force  # Force install
  node scripts/install-commands.js --info   # Check installation status
`);
    return;
  }

  const installer = new CommandInstaller();

  try {
    if (info) {
      await showInstallationInfo(installer);
    } else if (uninstall) {
      await uninstallCommands(installer);
    } else {
      await installCommands(installer, force);
    }
  } catch (error) {
    logger.error('Script execution failed:', error);
    process.exit(1);
  }
}

async function installCommands(installer, force) {
  try {
    logger.info('Starting SSH command documentation installation...');
    
    if (force) {
      logger.info('Force mode enabled - will overwrite existing files');
    }
    
    const installInfo = await installer.getInstallationInfo();
    
    if (installInfo.isInstalled && !force) {
      logger.info('Command documentation is already installed');
      logger.info(`Location: ${installInfo.directory}`);
      logger.info(`Installed files: ${installInfo.installedFiles.length}`);
      
      if (installInfo.missingFiles.length > 0) {
        logger.info(`Missing files: ${installInfo.missingFiles.join(', ')}`);
        logger.info('Installing missing files...');
        
        for (const filename of installInfo.missingFiles) {
          await installer.updateCommandFile(filename);
        }
      }
      
      logger.info('Use --force to reinstall all files');
      return;
    }
    
    await installer.installCommands(force);
    
    // Show installation result
    const newInstallInfo = await installer.getInstallationInfo();
    logger.info('Installation completed successfully!');
    logger.info(`Location: ${newInstallInfo.directory}`);
    logger.info(`Total files: ${newInstallInfo.installedFiles.length}`);
    logger.info(`Files: ${newInstallInfo.installedFiles.join(', ')}`);
    
  } catch (error) {
    logger.error('Installation failed:', error);
    throw error;
  }
}

async function uninstallCommands(installer) {
  try {
    logger.info('Starting SSH command documentation removal...');
    
    const installInfo = await installer.getInstallationInfo();
    
    if (!installInfo.isInstalled) {
      logger.info('Command documentation is not installed');
      return;
    }
    
    logger.info(`Removing ${installInfo.installedFiles.length} files from ${installInfo.directory}`);
    
    await installer.uninstallCommands();
    
    logger.info('Uninstallation completed successfully!');
    
  } catch (error) {
    logger.error('Uninstallation failed:', error);
    throw error;
  }
}

async function showInstallationInfo(installer) {
  try {
    const info = await installer.getInstallationInfo();
    
    console.log('\n=== SSH MCP Commands Installation Info ===');
    console.log(`Status: ${info.isInstalled ? 'INSTALLED' : 'NOT INSTALLED'}`);
    console.log(`Directory: ${info.directory}`);
    console.log(`Installed files (${info.installedFiles.length}):`);
    
    if (info.installedFiles.length > 0) {
      info.installedFiles.forEach(file => console.log(`  ✓ ${file}`));
    } else {
      console.log('  (none)');
    }
    
    if (info.missingFiles.length > 0) {
      console.log(`Missing files (${info.missingFiles.length}):`);
      info.missingFiles.forEach(file => console.log(`  ✗ ${file}`));
    }
    
    console.log('');
    
  } catch (error) {
    logger.error('Failed to get installation info:', error);
    throw error;
  }
}

// Run the script
main().catch(error => {
  console.error('Script failed:', error);
  process.exit(1);
});