source_directory_list = ['treedict']
compiler_args = []
link_args = []
# Stuff for extension module stuff
extra_library_dirs = []
extra_include_dirs = []

library_includes = []
specific_libraries = {}
################################################################################
# Shouldn't have to adjust anything below this line...

from glob import glob
import os
from os.path import split, join
from itertools import chain
import sys

from setuptools.extension import Extension

######################################################
# First have to see if we're authorized to use cython files, or if we
# should instead compile the included files


if "--debug" in sys.argv:
    debug_mode_c_code = True
    del sys.argv[sys.argv.index("--debug")]
else:
    debug_mode_c_code = False

# Get all the cython files in the sub directories and in this directory
cython_files = dict( (d, glob(join(d, "*.pyx"))) for d in source_directory_list + ['.'])


# see if we have python 3 support
if sys.version_info[0] > 2:
    compiler_args.append("-DPYTHON3")

all_cython_files = set(chain(*list(cython_files.values())))

print("+++++++++++++++++++")

print("Cython Files Found: \n%s\n+++++++++++++++++++++" % ", ".join(sorted(all_cython_files)))

# Set the compiler arguments -- Add in the environment path stuff
ld_library_path = os.getenv("LD_LIBRARY_PATH")

if ld_library_path is not None:
    lib_paths = ld_library_path.split(":")
else:
    lib_paths = []

include_path = os.getenv("INCLUDE_PATH")
if include_path is not None:
    include_paths = [p.strip() for p in include_path.split(":") if len(p.strip()) > 0]
else:
    include_paths = []


# get all the c files that are not cythonized .pyx files.
c_files   = dict( (d, [f for f in glob(join(d, "*.c"))
                       if (f[:-2] + '.pyx') not in all_cython_files])
                  for d in source_directory_list + ['.'])

for d, l in chain(((d, glob(join(d, "*.cxx"))) for d in source_directory_list + ['.']),
                  ((d, glob(join(d, "*.cpp"))) for d in source_directory_list + ['.'])):
    c_files[d] += l


print("C Extension Files Found: \n%s\n+++++++++++++++++++++" % ", ".join(sorted(chain(*list(c_files.values())))))

# Collect all the python modules
def get_python_modules(f):
    d, m = split(f[:f.rfind('.')])
    return m if len(d) == 0 else d + "." + m

exclude_files = set(["setup.py","build.py"])
python_files = set(chain(* (list(glob(join(d, "*.py")) for d in source_directory_list) + [glob("*.py")]))) 
python_files -= exclude_files

python_modules = [get_python_modules(f) for f in python_files]

print("Relevant Python Files Found: \n%s\n+++++++++++++++++++++" % ", ".join(sorted(python_files)))

def strip_empty(l):
    return [e.strip() for e in l if len(e.strip()) != 0]

def get_include_dirs(m):
    return strip_empty(extra_include_dirs + include_paths)

def get_library_dirs(m):
    return strip_empty(extra_library_dirs + lib_paths)

def get_libraries(m):
    return strip_empty(library_includes + (specific_libraries[m] if m in specific_libraries else []))

def get_extra_compile_args(m):
    return strip_empty(compiler_args + (['-g', '-O0', '-UNDEBUG']
                                        if debug_mode_c_code
                                        else ['-DNDEBUG']))

def get_extra_link_args(m):
    return strip_empty(link_args + (['-g'] if debug_mode_c_code else []))


############################################################
# Cython extension lists
from Cython.Build import cythonize
def makeExtensionList(d, filelist):
    ext_modules = []

    for f in filelist:
        f_no_ext = f[:f.rfind('.')]
        f_mod = split(f_no_ext)[1]
        modname = "%s.%s" % (d, f_mod) if d != '.' else f_mod
        
        ext_modules.append(Extension(
                modname,
                [f],
                include_dirs = get_include_dirs(modname),
                library_dirs = get_library_dirs(modname),
                libraries = get_libraries(modname),
                extra_compile_args = get_extra_compile_args(modname),
                extra_link_args = get_extra_link_args(modname)
                
                ))

    return cythonize(ext_modules,compiler_directives={'language_level' : "2"})

############################################################
# Now get all these ready to go

ext_modules = []


from Cython.Distutils import build_ext

ext_modules += list(chain(*list(makeExtensionList(d, l) 
                                for d, l in cython_files.items())))

cmdclass = {'build_ext' : build_ext}


ext_modules += list(chain(*list(makeExtensionList(d, l)
                                for d, l in c_files.items())))
def build(setup_kwargs):
    setup_kwargs.update(
        dict(
            cmdclass=cmdclass,
            ext_modules=ext_modules,
            py_modules = python_modules
            #zip_safe=False
        )
    )
