from aiida.engine import get_daemon_client
from merger import merger
from pathlib import Path
from profiling import InjectTool, profile_function_call
from submission_controller import add_in_batches
import shutil
import csv

from aiida import engine, orm

func_to_profile_transport = [
    "__init__",
    "open",
    "close",
    "chdir",
    "normalize",
    "getcwd",
    "makedirs",
    "mkdir",
    "rmtree",
    "rmdir",
    "chown",
    "isdir",
    "chmod",
    "put",
    "putfile",
    "puttree",
    "get",
    "getfile",
    "gettree",
    "get_attribute",
    "copyfile",
    "copytree",
    "copy",
    "listdir",
    "remove",
    "rename",
    "isfile",
    "_exec_command_internal",
    "exec_command_wait_bytes",
    "gotocomputer_command",
    "symlink",
    "path_exists",
    # "whoami"
]

func_to_profile_scheduler = [
    "submit_job",
    "get_jobs",
    "kill_job",
]


import os
import sys


def find_file_in_python_path(filename):
    for directory in sys.path:
        potential_path = os.path.join(directory, filename)
        if os.path.isfile(potential_path):
            return os.path.abspath(potential_path)
    raise FileNotFoundError(f"Couldn't fine {filename} python_path")


src_files = {
    "src_transport_ssh": "aiida/transports/plugins/ssh.py",
    "src_scheduler_ssh": "aiida/schedulers/plugins/bash.py",
    "src_scheduler": "aiida/schedulers/scheduler.py",
    "src_transport_fire": "aiida_firecrest/transport.py",
    "src_scheduler_fire": "aiida_firecrest/scheduler.py",
}


out_path = "out/"

profile_results = out_path + "{0}/"
# shutil.rmtree(profile_results, ignore_errors=True)

from aiida.engine.daemon.client import DaemonNotRunningException


def per_plugin(plugin_: str = ""):
    """
    This is the core function of the script, responsible for profiling the specified backend plugin (`ssh` or `fire`). It:
        1. Locates the appropriate source files.
        2. Manages the AiiDA daemon, ensuring it stops and starts as needed for clean testing.
        3. Patches the functions in the transport and scheduler modules to profile them using the `InjectTool` and `profile_function_call`.
        4. Runs batch job submissions using `add_in_batches`, capturing the total execution time for different batch sizes.
        5. Merges and logs the profiling results using `merger`.
        6. Cleans up by restoring the original files and stopping the daemon.
        7. Returns the number of jobs and the total time taken for those jobs.

    plugin_: str
        either 'ssh' or 'fire'
    """
    tot_time = []
    numjobs = []

    src_transport_plugin = find_file_in_python_path(f"src_transport_{plugin_}")
    src_scheduler_plugin = find_file_in_python_path(f"src_scheduler_{plugin_}")
    src_scheduler = find_file_in_python_path(f"src_scheduler")

    client = get_daemon_client(profile_name="a")

    for i in range(1, 5):

        Grouplabel_ = f"{plugin_}_{i**2}"

        # you could add deletion of the group here
        # try:
        #     orm.Group.collection.get(label=Glabel_ssh)
        #     orm.Group.collection.delete(label=Glabel_ssh)

        # except NotExistent as exc:
        #     pass

        profile_results_ = profile_results.format(Grouplabel_)

        shutil.rmtree(profile_results_, ignore_errors=True)
        Path(profile_results_).mkdir(exist_ok=True)

        with InjectTool() as inj:

            try:
                client.stop_daemon(wait=True)
            except DaemonNotRunningException:
                pass

            inj.patcher(
                src_transport_plugin,
                func_to_profile_transport,
                profile_function_call,
                profile_results_,
            )
            inj.patcher(
                src_scheduler_plugin,
                func_to_profile_scheduler,
                profile_function_call,
                profile_results_,
            )
            inj.inject_attribute(src_transport_plugin, "__init__", "profiling", 0)
            inj.inject_attribute(src_scheduler, "__init__", "profiling", 0)

            client.start_daemon(number_workers=4)
            assert client.is_daemon_running

            if plugin_ == "fire":
                add_in_batches("add@tds3", i, group_label_=Grouplabel_)
            elif plugin_ == "ssh":
                add_in_batches(
                    "add@SSH_tds", i, group_label_=Grouplabel_
                )  # "add@tutor"

            client.stop_daemon(wait=True)

            # I use `skipNotfound=True` because some times client.stop_daemon would also restore the patched files, weird.
            inj.restore(skipNotfound=True)

        merger_res = merger(profile_results_, sortby="tottime")

        tot_time.append(float(merger_res.split()[-2]))
        numjobs.append(i**2)

    return numjobs, tot_time


# here is the part we profile the ssh and firecrest plugins
ssh_data = per_plugin(plugin_="ssh")
fire_data = per_plugin(plugin_="fire")

# now, wrrtting out the results
with open(out_path + "SSH.csv", "w", newline="") as csvfile:
    writer = csv.writer(csvfile)
    writer.writerow(["numjobs", "tot_time"])
    writer.writerows(list(zip(ssh_data[0], ssh_data[1])))

with open(out_path + "Fire.csv", "w", newline="") as csvfile:
    writer = csv.writer(csvfile)
    writer.writerow(["numjobs", "tot_time"])
    writer.writerows(list(zip(fire_data[0], fire_data[1])))


from profiling.plotter import all_in_one

fig, ax, plt = all_in_one(
    path_=out_path,
    xcolum="numjobs",
    ycolum="tot_time",
    xlabel="Number of jobs (batch submission)",
    ylabel="Total time (s)",
    title="SSH vs FirecREST",
    save_name="SSH_vs_FirecREST.png",
)
