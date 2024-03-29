import sys
import platform
import subprocess
import multiprocessing


def is_web() -> bool:
    """ Check if the application is running on web. """
    return sys.platform.lower() == "emscripten"


def get_cpu_info() -> dict:
    """
    Gather CPU information.

    Returned dictionary consists of these information:
    - name:  Processor name. (eg. Intel(R) Core(TM) i5-9300H CPU @ 2.4GHz)
    - model: Vague processor name returned by platform.processor(). (eg. Intel64 Family 6 Model 42 Stepping 7, GenuineIntel)
    - brand: Brand/company name. (eg. Intel)
    - is_64: Whether the processor architecture is 64-bit or not.
    - cores: Number of cores the processor has.

    @return Info dict
    """

    # This SO thread has lots of good information about parsing CPU info
    # https://stackoverflow.com/questions/4842448/getting-processor-information-in-python

    # Default processor name to fall back to if parsing fails
    def_name = platform.processor()

    name = ""

    # Try wmic command on Windows
    if platform.system() == "Windows":
        try:
            out = subprocess.check_output("wmic cpu get name", shell=True)
            name = out.decode("utf-8").strip().split("\n")[1]

        except:
            name = def_name

    # Try parsing /proc/cpuinfo on Linux
    elif platform.system() == "Linux":
        try:
            out = subprocess.check_output("cat /proc/cpuinfo", shell=True)
            lines = out.decode("utf-8").strip().split("\n")

            for line in lines:
                if line.startswith("model name"):
                    name = line.split(":")[1]
                    break

            # /proc/cpuinfo doesn't have model name field
            if name == "": name = def_name

        except:
            name = def_name

    # No OSX support yet ¯\_(ツ)_/¯

    if "intel" in name.lower():
        brand = "Intel"

    elif "amd" in name.lower():
        brand = "AMD"

    else:
        # Just hope brand name happens to be in the beginning
        brand = name.split()[0]
        
    return {
        "name": name,
        "model": def_name,
        "brand": brand,
        "is_64": "64" in platform.architecture()[0],
        "cores": multiprocessing.cpu_count()
    }