import glob
import os

import yara

from server import objects


class ScanYara(objects.StrelkaScanner):
    """Scans files with YARA.

    Attributes:
        compiled_yara: Compiled YARA file derived from YARA rule file(s)
            in location.

    Options:
        location: Location of the YARA rules file or directory.
            Defaults to "/etc/yara/".
        metadata_identifiers: List of YARA rule metadata identifiers
            (e.g. "Author") that should be logged as metadata.
            Defaults to empty list.
    """
    def init(self):
        self.compiled_yara = None

    def scan(self, file_object, options):
        location = options.get("location", "/etc/yara/")
        metadata_identifiers = options.get("metadata_identifiers", [])

        try:
            if self.compiled_yara is None:
                if os.path.isdir(location):
                    yara_filepaths = {}
                    globbed_yara_paths = glob.iglob(f"{location}/**/*.yar*", recursive=True)
                    for (idx, entry) in enumerate(globbed_yara_paths):
                        yara_filepaths[f"namespace_{idx}"] = entry
                    self.compiled_yara = yara.compile(filepaths=yara_filepaths)

                else:
                    self.compiled_yara = yara.compile(filepath=location)

        except (yara.Error, yara.SyntaxError) as YaraError:
            file_object.flags.append(f"{self.scanner_name}::compiling_error")

        self.metadata.setdefault("matches", [])
        self.metadata.setdefault("metadata", [])
        try:
            if self.compiled_yara is not None:
                yara_matches = self.compiled_yara.match(data=file_object.data)
                for match in yara_matches:
                    self.metadata["matches"].append(match.rule)
                    if metadata_identifiers and match.meta:
                        for (key, value) in match.meta.items():
                            if key in metadata_identifiers:
                                yara_entry = {"rule": match.rule,
                                              "identifier": key,
                                              "value": value}
                                if yara_entry not in self.metadata["metadata"]:
                                    self.metadata["metadata"].append(yara_entry)

        except (yara.Error, yara.TimeoutError) as YaraError:
            file_object.flags.append(f"{self.scanner_name}::scanning_error")
