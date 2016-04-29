# Python 3.4 program to recursively scan from current folder
# or folder dropped onto file or specificed in command line
# for every file with an extension in the exts list:
# check if file's album tag is "recompressed", if not recompress it, and add that tag
# then rename/overwrite of OVERWRITE = True
#
# Copy ffmpeg and ffprobe into the same folder as this script.

import sys
import subprocess
import os
from pathlib import Path
import shlex
import re

def escape_argument(arg):
    # From http://stackoverflow.com/a/29215357/1499289
    # Escape the argument for the cmd.exe shell.
    # See http://blogs.msdn.com/b/twistylittlepassagesallalike/archive/2011/04/23/everyone-quotes-arguments-the-wrong-way.aspx
    #
    # First we escape the quote chars to produce a argument suitable for
    # CommandLineToArgvW. We don't need to do this for simple arguments.

    if not arg or re.search(r'(["\s])', arg):
        arg = '"' + arg.replace('"', r'\"') + '"'

    return escape_for_cmd_exe(arg)


def escape_for_cmd_exe(arg):
    # Escape an argument string to be suitable to be passed to
    # cmd.exe on Windows
    #
    # This method takes an argument that is expected to already be properly
    # escaped for the receiving program to be properly parsed. This argument
    # will be further escaped to pass the interpolation performed by cmd.exe
    # unchanged.
    #
    # Any meta-characters will be escaped, removing the ability to e.g. use
    # redirects or variables.
    #
    # @param arg [String] a single command line argument to escape for cmd.exe
    # @return [String] an escaped string suitable to be passed as a program
    #   argument to cmd.exe

    meta_chars = '()%!^"<>&|'
    meta_re = re.compile('(' + '|'.join(re.escape(char) for char in list(meta_chars)) + ')')
    meta_map = { char: "^%s" % char for char in meta_chars }

    def escape_meta_chars(m):
        char = m.group(1)
        return meta_map[char]

    return meta_re.sub(escape_meta_chars, arg)

def isRecompressed(inputPath):
    # runs ffprobe to read the album tag, returns True if tag exists and equals "recompressed"
    cmd = os.path.join(__location__,"ffprobe") + ' -hide_banner -of default=noprint_wrappers=1  -show_entries format_tags=album -v quiet '+str(inputPath)
    probe = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, shell=True)
    output, outputError = probe.communicate()
    print(output, outputError)
    output = output.strip().decode('utf-8')
    if len(output) < 1: return False
    return (output.split('=')[1] == "recompressed")

def doRecompress(inputPath, outputPath):
    # runs ffmpeg to recompress to crf 23 (this approx halves size of ipad 720p videos)
    # sets the album tag to "recompressed"
    cmd = os.path.join(__location__,"ffmpeg") + ' -hide_banner -v quiet -i '+str(inputPath)+' -metadata album="recompressed" \
          -c:v libx264 -preset slow -crf 23 -acodec copy '+str(outputPath)
    #test command that does not recompress
    #cmd = os.path.join(__location__,"ffmpeg") + ' -hide_banner -v quiet -i '+str(inputPath)+' -metadata album="recompressed" \
    #      -c copy '+str(outputPath)
    print(cmd)
    try:
        probe = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, shell=True)
        output, outputError = probe.communicate()
        returncode = 0
        print(output, outputError)
    except CalledProcessError as e:
        print("ffmpeg returned error", e.returncode)
        returncode = e.returncode
    return (returncode == 0)

def overwriteFile(inputPath, outputPath):
    # renames original file to add .original to the end (uncomment next line to delete it instead
    #os.remove(str(inputPath))
    os.rename(str(inputPath), str(inputPath)+".original")
    os.rename(str(outputPath), str(inputPath))

def shrinkFile(inputPath):
    # create a filename with -shrunk before the extension
    name = str(inputPath.stem)
    name = name + "-shrunk" + str(inputPath.suffix)
    outputPath = inputPath.with_name(name)

    # escape paths, Windows or standard shell
    if os.name == "nt":
        inputPathEsc = escape_argument(str(inputPath))
        outputPathEsc = escape_argument(str(outputPath))
    else:
        inputPathEsc = shlex.quote(str(inputPath))
        outputPathEsc = shlex.quote(str(outputPath))

    #read metadata 
    alreadyProcessed = isRecompressed(inputPathEsc)
    if alreadyProcessed:
        print("File "+str(inputPath)+" already recompressed")
        success = False
    else:
        #recompress file
        success = doRecompress(inputPathEsc, outputPathEsc)

    # if recompression worked, and as a final recheck, the album tag is now "recompressed", overwrite original file (actually rename)
    if success and isRecompressed(outputPathEsc):
        print("New file has recompressed metadata")
        if OVERWRITE:
            overwriteFile(inputPath, outputPath)

# OVERWRITE = True calls overwriteFile, which, by default, just renames
# OVERWRITE = False would leave the original file, and a file named filename-shrunk.ext
OVERWRITE = True

__location__ = os.path.realpath(os.path.join(os.getcwd(), os.path.dirname(__file__)))

# If you don't drag a folder or run with an extension, attempt to use folder script is run from
if len(sys.argv) > 1:
  i = sys.argv[1]
else:
  i = __location__
print(i)
exts = ['mov', 'MOV', 'mp4', 'MP4', 'm4v', 'M4V']

for ext in exts:
    files = sorted(Path(i).glob('**/*.'+ext))
    for file in files:
        shrinkFile(file)
a = input("Done, press Enter")
