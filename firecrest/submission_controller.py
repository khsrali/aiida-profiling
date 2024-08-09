# -*- coding: utf-8 -*-
"""An example of a SubmissionController implementation to compute a dimensionxdimension table of additions."""
import time

from aiida import orm
from aiida.calculations.arithmetic.add import ArithmeticAddCalculation
from pydantic import field_validator

from aiida_submission_controller import BaseSubmissionController
from aiida import load_profile
from aiida.engine import run, submit

load_profile()


class AdditionTableSubmissionController(BaseSubmissionController):
    """The implementation of a SubmissionController to compute a dimensionxdimension table of additions."""

    code_label: str
    dimension: int
    """Label of the `code.arithmetic.add` `Code`."""

    @field_validator("code_label")
    def _check_code_plugin(cls, value):
        plugin_type = orm.load_code(value).default_calc_job_plugin
        if plugin_type == "core.arithmetic.add":
            return value
        raise ValueError(
            f"Code with label `{value}` has incorrect plugin type: `{plugin_type}`"
        )

    def get_extra_unique_keys(self):
        """Return a tuple of the keys of the unique extras that will be used to uniquely identify your workchains.

        Here I will use the value of the two integer operands as unique identifiers.
        """
        return ["left_operand", "right_operand"]

    def get_all_extras_to_submit(self):
        """I want to compute a dimensionxdimension table.

        I will return therefore the following list of tuples: [(1, 1), (1, 2), ..., (dimension, dimension)].
        """
        all_extras = set()
        for left_operand in range(1, self.dimension + 1):
            for right_operand in range(1, self.dimension + 1):
                all_extras.add((left_operand, right_operand))
        return all_extras

    def get_inputs_and_processclass_from_extras(self, extras_values):
        """Return inputs and process class for the submission of this specific process.

        I just submit an ArithmeticAdd calculation summing the two values stored in the extras:
        ``left_operand + right_operand``.
        """
        builder = ArithmeticAddCalculation.get_builder()
        builder.code = orm.load_code(self.code_label)
        builder.x = orm.Int(extras_values[0])
        builder.y = orm.Int(extras_values[1])
        builder.metadata.options.account = "mr32"
        builder.metadata.options.custom_scheduler_commands = (
            "#SBATCH --constraint=mc\n#SBATCH --mem=10K"
        )

        return builder


def add_in_batches(
    code_label_: str, dimension: int = 12, group_label_: str = "addition_table"
):
    """Run the simulations defined in this class, as a showcase of the functionality of this class."""
    import sys  # pylint: disable=import-outside-toplevel

    ## IMPORTANT: make sure that you have a `add@localhost` code, that you can setup (once you have a
    ## localhost computer) using the following command, for instance:
    ##
    ##  verdi code setup -L add --on-computer --computer=localhost -P core.arithmetic.add --remote-abs-path=/bin/bash -n
    # Create a controller
    this_is_the_end = False

    group, _ = orm.Group.collection.get_or_create(label=f"tests/{group_label_}")

    controller = AdditionTableSubmissionController(
        code_label=code_label_,
        group_label=group.label,
        max_concurrent=10,
        dimension=dimension,
    )

    while True:
        print("Max concurrent :", controller.max_concurrent)
        print("Active slots   :", controller.num_active_slots)
        print("Available slots:", controller.num_available_slots)
        print("Already run    :", controller.num_already_run)
        print("Still to run   :", controller.num_to_run)
        print()

        if controller.num_to_run == 0 and controller.num_active_slots == 0:
            this_is_the_end = True

        ## Uncomment the following two lines if you just want to do a dry-run without actually submitting anything
        # print("I would run next:")
        # print(controller.submit_new_batch(dry_run=True))

        print("Let's run a new batch!")
        # Note: the number might differ from controller.num_available_slots shown above, as some more
        # calculations might be over in the meantime.
        run_processes = controller.submit_new_batch(dry_run=False)
        for run_process_extras, run_process in run_processes.items():
            print(f"{run_process_extras} --> PK = {run_process.pk}")

        print()

        ## Print results
        print(">>> RESULTS UP TO NOW:")
        print("    Legend:")
        print("      ###: not yet submitted")
        print("      ???: submitted, but no results (not finished or failed)")
        all_submitted = controller.get_all_submitted_processes()
        sys.stdout.write("   |")
        for right in range(1, dimension + 1):
            sys.stdout.write(f"{right:3d} ")
        sys.stdout.write("\n")
        sys.stdout.write("----" + "----" * dimension)
        sys.stdout.write("\n")

        # Print table
        for left in range(1, dimension + 1):
            sys.stdout.write(f"{left:2d} |")
            for right in range(1, dimension + 1):
                process = all_submitted.get((left, right))
                if process is None:
                    result = "###"  # No node
                else:
                    try:
                        result = f"{process.outputs.sum.value:3d}"
                    except AttributeError:
                        result = (
                            "???"  # Probably not completed, does not have output 'sum'
                        )
                sys.stdout.write(result + " ")
            sys.stdout.write("\n")

        time.sleep(2)

        if this_is_the_end:
            return


def add_single_job(code_label, x, y, action="submit"):
    """Do some aiida stuff

    Parameters
    ----------
    code_label : str
        The code label
    x : int
    y : int
    action : str
        'submit' or 'run'
    """

    codeREMO = orm.load_code(label=code_label)
    builderREMO = codeREMO.get_builder()
    builderREMO.x = orm.Int(x)
    builderREMO.y = orm.Int(y)
    builderREMO.metadata.options.account = "mr32"
    builderREMO.metadata.options.custom_scheduler_commands = (
        "#SBATCH --constraint=mc\n#SBATCH --mem=10K"
    )

    if action == "submit":
        submit(builderREMO)
    else:
        run(builderREMO)
