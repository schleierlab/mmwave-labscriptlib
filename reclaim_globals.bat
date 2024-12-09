@Echo Repacking globals.h5 ...
@echo off
h5repack globals.h5 globals_repacked.h5
del globals_backup.h5
ren globals.h5 globals_backup.h5
ren globals_repacked.h5 globals.h5
@Echo done