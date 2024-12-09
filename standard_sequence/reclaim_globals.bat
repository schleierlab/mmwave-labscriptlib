@Echo Repacking globals.h5 ...
@echo off
call C:\Users\sslab\miniconda3\condabin\activate.bat labscript-env
h5repack standard_sequence.h5 globals_repacked.h5
del globals_backup.h5
ren standard_sequence.h5 globals_backup.h5
ren globals_repacked.h5 standard_sequence.h5
@Echo done