import uuid
import cProfile
import os
import atexit


def profile_function_call(profile_path):
    """Decorator to profile a function call.
    The profile will be dumped to the specified path.

    :param profile_path: (str) the abs path where the profile will be dumped"""

    def decorator(func):
        def wrapper(self, *args, **kwargs):
            if hasattr(self, "profiling") and not self.profiling:
                profiler = cProfile.Profile()
                profiler.enable()
                self.profiling = True

                result = func(self, *args, **kwargs)

                profiler.disable()
                self.profiling = False

                profiler.dump_stats(
                    f"{profile_path}/{func.__name__}-{uuid.uuid4()}.prof"
                )
            else:
                result = func(self, *args, **kwargs)

            return result

        return wrapper

    return decorator


class InjectTool:

    def __init__(self):

        self._BACKUP_NAME = "__profiling__backup__"
        self.patched_files = []

    def __enter__(self):
        atexit.register(self.restore, skipNotfound=True)
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        # This cannot to handle SIGISTP, and SIGINT :
        # self.restore(skipNotfound=True)
        # that's why we use atexit.register an __enter__
        pass

    def patcher(
        self, source_file, func_names: list, decorator, *input_args, skipNotfound=False
    ):
        """This function patches a decorator to any function in the source code

        Note: AiiDA design permits it to be called from multiple resources, daemon, cmdline, scripts, etc.
        right now, the simplest solution is simply add the decorator on the function definition.
        therefore this code is modifying your source code. Once test are done, either success or failure, original source code is reverted.
        The ideal long term solution would be to make a docker container with the patched code and run the tests there.

        :param source_file: (str) the source file to be patched
        :param func_names: list(str) the function names to be patched
        :param decorator: (function) the patch
        :param input_args: (tuple) the input arguments for the decorator
        :param skipNotfound: (bool) if True, the function will not raise an error if the function is not found
            default is False
        """

        backup_file = source_file + self._BACKUP_NAME
        decorator__name__ = decorator.__name__

        with open(source_file, "r") as f:
            source_code = f.read()

        if not os.path.exists(backup_file):
            with open(backup_file, "w") as f:
                f.write(source_code)

        # I don't want to install this package yet, so I'm adding the path to the sys.path
        if "import profile_function_call" not in source_code:
            import_statement = "from profiling import profile_function_call\n\n"
            annotation_statement = "from __future__ import annotations\n"
            # it's wrriten this wat
            if annotation_statement in source_code:
                source_code = source_code.replace(
                    annotation_statement, f"{annotation_statement}\n{import_statement}"
                )
            else:
                source_code = f"{import_statement}{source_code}"

        for func_name in func_names:

            index_func = source_code.find(f"def {func_name}(")

            if index_func == -1:
                if skipNotfound:
                    continue
                else:
                    raise ValueError(f"Function {func_name} not found in {source_file}")

            index_i = source_code.rfind("\n", 0, index_func)
            insert_string = (
                " " * (index_func - index_i - 1) + f"@{decorator__name__}{input_args}\n"
            )
            source_code = (
                source_code[: index_i + 1] + insert_string + source_code[index_i + 1 :]
            )

        with open(source_file, "w") as f:
            f.write(source_code)
            self.patched_files.append(source_file)

    def inject_attribute(
        self,
        source_file,
        func_name,
        attribute_name,
        attribute_value,
    ):
        """This function inject an attribute to a class

        :param source_file: (str) the source file to be patched
        :param func_name: (str) the function name to be patched
        :param attribute_name: (str) the attribute name to be added
        :param attribute_value: (str) the attribute value to be added
        """

        backup_file = source_file + self._BACKUP_NAME

        with open(source_file, "r") as f:
            source_code = f.readlines()

        if not os.path.exists(backup_file):
            with open(backup_file, "w") as f:
                f.writelines(source_code)

        index_func = next(
            (
                i
                for i, line in enumerate(source_code)
                if line.strip().startswith(f"def {func_name}(")
            ),
            -1,
        )
        if index_func == -1:
            raise ValueError(f"Function {func_name} not found in {source_file}")

        index_end_def = next(
            (
                i
                for i, line in enumerate(source_code[index_func:], start=index_func)
                if "):" in line
            ),
            -1,
        )
        if index_end_def == -1:
            raise ValueError(
                f"Function {func_name} definition not properly closed in {source_file}"
            )

        insert_string = (
            " "
            * (
                4
                + len(source_code[index_end_def])
                - len(source_code[index_end_def].lstrip())
            )
            + f"self.{attribute_name} = {attribute_value}\n"
        )

        source_code.insert(index_end_def + 1, insert_string)

        with open(source_file, "w") as f:
            f.writelines(source_code)
            self.patched_files.append(source_file)

    def restore(self, skipNotfound=False):
        """This function unpatches the source code

        :param source_file:"""

        for source_file in self.patched_files:

            backup_file = source_file + self._BACKUP_NAME

            try:
                with open(backup_file, "r") as f:
                    source_code = f.read()
            except FileNotFoundError as e:
                if skipNotfound:
                    continue
                else:
                    raise e

            with open(source_file, "w") as f:
                f.write(source_code)

            os.remove(backup_file)

        self.patched_files = []
