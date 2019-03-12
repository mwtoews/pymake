import os
import sys
import shutil
import platform

from .pymake import main
from .download import download_and_unzip
from .usgsurls import usgs_prog_data

def build_program(target='mf2005', fc='gfortran', cc='gcc', makeclean=True,
                  expedite=False, dryrun=False, double=False, debug=False,
                  include_subdirs=False, fflags=None, arch='intel64',
                  makefile=False, srcdir2=None, extrafiles=None,
                  download_dir=None, download=True,
                  exe_name=None, target_dir=None,
                  replace_function=None, verify=True, modify_exe_name=True):
    if exe_name is None:
        exe_name = target

    if modify_exe_name:
        if double:
            filename, file_extension = os.path.splitext(exe_name)
            if 'dbl' not in filename.lower():
                exe_name = filename + 'dbl' + file_extension
        if debug:
            filename, file_extension = os.path.splitext(exe_name)
            if filename.lower()[-1] != 'd':
                exe_name = filename + 'd' + file_extension

    if platform.system().lower() == 'windows':
        filename, file_extension = os.path.splitext(exe_name)
        if file_extension.lower() is not '.exe':
            exe_name += '.exe'

    if target_dir is not None:
        exe_name = os.path.abspath(os.path.join(target_dir, exe_name))

    # extract program data for target
    prog_dict = usgs_prog_data.get_target(target)

    # set url
    url = prog_dict.url

    # Set dir name
    dirname = prog_dict.dirname
    if download_dir is None:
        dirname = './'
    else:
        dirname = os.path.join(download_dir, dirname)

    # Set srcdir name
    srcdir = prog_dict.srcdir
    srcdir = os.path.join(dirname, srcdir)

    # Download the distribution
    if download:
        download_and_unzip(url, verify=verify, pth=download_dir)

    if replace_function is not None:
        print('replacing select source files for {}'.format(target))
        replace_function(srcdir, fc, cc, arch)

    # compile code
    print('compiling...{}'.format(os.path.relpath(exe_name)))
    main(srcdir, exe_name, fc=fc, cc=cc, makeclean=makeclean,
         expedite=expedite, dryrun=dryrun, double=double, debug=debug,
         include_subdirs=include_subdirs, fflags=fflags, arch=arch,
         makefile=makefile, srcdir2=srcdir2, extrafiles=extrafiles)

    if verify:
        app = os.path.relpath(exe_name)
        msg = '{} does not exist.'.format(app)
        assert os.path.isfile(exe_name), msg

    return


# routines for updating source files to compile with gfortran
def update_mt3dfiles(srcdir, fc, cc, arch):
    # Replace the getcl command with getarg
    f1 = open(os.path.join(srcdir, 'mt3dms5.for'), 'r')
    f2 = open(os.path.join(srcdir, 'mt3dms5.for.tmp'), 'w')
    for line in f1:
        f2.write(line.replace('CALL GETCL(FLNAME)', 'CALL GETARG(1,FLNAME)'))
    f1.close()
    f2.close()
    os.remove(os.path.join(srcdir, 'mt3dms5.for'))
    shutil.move(os.path.join(srcdir, 'mt3dms5.for.tmp'),
                os.path.join(srcdir, 'mt3dms5.for'))

    # Replace filespec with standard fortran
    l = '''
          CHARACTER*20 ACCESS,FORM,ACTION(2)
          DATA ACCESS/'STREAM'/
          DATA FORM/'UNFORMATTED'/
          DATA (ACTION(I),I=1,2)/'READ','READWRITE'/
    '''
    fn = os.path.join(srcdir, 'FILESPEC.INC')
    f = open(fn, 'w')
    f.write(l)
    f.close()

    return


def update_seawatfiles(srcdir, fc, cc, arch):
    # Remove the parallel and serial folders from the source directory
    dlist = ['parallel', 'serial']
    for d in dlist:
        dname = os.path.join(srcdir, d)
        if os.path.isdir(dname):
            print('Removing ', dname)
            shutil.rmtree(os.path.join(srcdir, d))

    # rename all source files to lower case so compilation doesn't
    # bomb on case-sensitive operating systems
    srcfiles = os.listdir(srcdir)
    for filename in srcfiles:
        src = os.path.join(srcdir, filename)
        dst = os.path.join(srcdir, filename.lower())
        if 'linux' in sys.platform or 'darwin' in sys.platform:
            os.rename(src, dst)

    if 'linux' in sys.platform or 'darwin' in sys.platform:
        updfile = False
        if 'icc' in cc or 'clang' in cc:
            updfile = True
        if updfile:
            fpth = os.path.join(srcdir, 'gmg1.f')
            lines = [line.rstrip() for line in open(fpth)]
            f = open(fpth, 'w')
            for line in lines:
                if "      !DEC$ ATTRIBUTES ALIAS:'_resprint' :: RESPRINT" in line:
                    line = "C      !DEC$ ATTRIBUTES ALIAS:'_resprint' :: RESPRINT"
                f.write('{}\n'.format(line))
            f.close()
    else:
        # must be windows
        if arch == 'intel64':
            fpth = os.path.join(srcdir, 'gmg1.f')
            lines = [line.rstrip() for line in open(fpth)]
            f = open(fpth, 'w')
            for line in lines:
                # comment out the 32 bit one and activate the 64 bit line
                if "C      !DEC$ ATTRIBUTES ALIAS:'resprint' :: RESPRINT" in line:
                    line = "       !DEC$ ATTRIBUTES ALIAS:'resprint' :: RESPRINT"
                if "      !DEC$ ATTRIBUTES ALIAS:'_resprint' :: RESPRINT" in line:
                    line = "C      !DEC$ ATTRIBUTES ALIAS:'_resprint' :: RESPRINT"
                f.write('{}\n'.format(line))
            f.close()

    return


def update_mf2000files(srcdir, fc, cc, arch):
    # Remove six src folders
    dlist = ['beale2k', 'hydprgm', 'mf96to2k', 'mfpto2k', 'resan2k', 'ycint2k']
    for d in dlist:
        dname = os.path.join(srcdir, d)
        if os.path.isdir(dname):
            print('Removing ', dname)
            shutil.rmtree(os.path.join(srcdir, d))

    # Move src files and serial src file to src directory
    tpth = os.path.join(srcdir, 'mf2k')
    files = [f for f in os.listdir(tpth) if
             os.path.isfile(os.path.join(tpth, f))]
    for f in files:
        shutil.move(os.path.join(tpth, f), srcdir)
    tpth = os.path.join(srcdir, 'mf2k', 'serial')
    files = [f for f in os.listdir(tpth) if
             os.path.isfile(os.path.join(tpth, f))]
    for f in files:
        shutil.move(os.path.join(tpth, f), srcdir)

    # Remove mf2k directory in source directory
    tpth = os.path.join(srcdir, 'mf2k')
    shutil.rmtree(tpth)


def update_mp6files(srcdir, fc, cc, arch):
    fname1 = os.path.join(srcdir, 'MP6Flowdata.for')
    f = open(fname1, 'r')

    fname2 = os.path.join(srcdir, 'MP6Flowdata_mod.for')
    f2 = open(fname2, 'w')
    for line in f:
        line = line.replace('CD.QX2', 'CD%QX2')
        f2.write(line)
    f.close()
    f2.close()
    os.remove(fname1)

    fname1 = os.path.join(srcdir, 'MP6MPBAS1.for')
    f = open(fname1, 'r')

    fname2 = os.path.join(srcdir, 'MP6MPBAS1_mod.for')
    f2 = open(fname2, 'w')
    for line in f:
        line = line.replace('MPBASDAT(IGRID)%NCPPL=NCPPL',
                            'MPBASDAT(IGRID)%NCPPL=>NCPPL')
        f2.write(line)
    f.close()
    f2.close()
    os.remove(fname1)


def update_mp7files(srcdir, fc, cc, arch):
    fpth = os.path.join(srcdir, 'StartingLocationReader.f90')
    with open(fpth) as f:
        lines = f.readlines()
    f = open(fpth, 'w')
    for line in lines:
        if 'pGroup%Particles(n)%InitialFace = 0' in line:
            continue
        f.write(line)
    f.close()


def update_vs2dtfiles(srcdir, fc, cc, arch):
    # move the main source into the source directory
    f1 = os.path.join(srcdir, '..', 'vs2dt3_3.f')
    f1 = os.path.abspath(f1)
    assert os.path.isfile(f1)
    f2 = os.path.join(srcdir, 'vs2dt3_3.f')
    f2 = os.path.abspath(f2)
    shutil.move(f1, f2)
    assert os.path.isfile(f2)

    f1 = open(os.path.join(srcdir, 'vs2dt3_3.f'), 'r')
    f2 = open(os.path.join(srcdir, 'vs2dt3_3.f.tmp'), 'w')
    for line in f1:
        srctxt = "     `POSITION='REWIND')"
        rpctxt = "     `POSITION='REWIND',ACCESS='STREAM')"
        f2.write(line.replace(srctxt, rpctxt))
    f1.close()
    f2.close()
    os.remove(os.path.join(srcdir, 'vs2dt3_3.f'))
    shutil.move(os.path.join(srcdir, 'vs2dt3_3.f.tmp'),
                os.path.join(srcdir, 'vs2dt3_3.f'))

    return
