import os


class Project:
    """
    This class provides access to the cutevariant project itself,
    providing methods to import new VCFs, compute metrics,...
    """

    def __init__(self, working_directory: str) -> None:
        self.workdir = working_directory

    def init_project(self):
        """
        Initialize this project by creating all the required files and directories.
        The directory should be empty when calling this method.
        """
        assert os.path.isdir(self.workdir), f"{self.workdir}: Not a directory!"
        assert not os.listdir(self.workdir), f"{self.workdir}: Directory not empty, aborting!"

        os.mkdir(os.path.join(self.workdir, "samples"))
        os.mkdir(os.path.join(self.workdir, "annotations"))
        os.mkdir(os.path.join(self.workdir, "original_vcfs"))

    def import_vcf(self, vcf_path: str, import_type=("variants", "annotations", "samples")):
        if "variants" in import_type:
            pass
