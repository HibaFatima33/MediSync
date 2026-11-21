"""Rebuild the three pipeline CSVs from the submission CSV parts."""
import argparse
import csv
import hashlib
import json
import shutil
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]


def file_hash(path):
    digest = hashlib.sha256()
    with path.open('rb') as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b''):
            digest.update(block)
    return digest.hexdigest()


def row_bytes(row):
    return (json.dumps(row, ensure_ascii=False, separators=(',', ':')) + '\n').encode('utf-8')


def restore(destination):
    source = ROOT / 'milestones' / 'Milestone.1.SDI.DWH' / 'oversampled_data'
    manifest = json.loads((source / 'manifest.json').read_text(encoding='utf-8'))
    destination = destination.resolve()
    existing = [destination / item['filename'] for item in manifest['datasets']]
    if any(path.exists() for path in existing):
        raise FileExistsError('CSV files already exist in this destination. Use a new empty folder to restore the submitted snapshot.')

    # Validate every part before producing any reconstructed source CSV.
    for dataset in manifest['datasets']:
        for part in dataset['parts']:
            if file_hash(source / part['path']) != part['sha256']:
                raise ValueError('Checksum mismatch for ' + part['path'])

    destination.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix='medisync_restore_', dir=destination.parent) as temporary:
        staging = Path(temporary)
        for dataset in manifest['datasets']:
            count = 0
            digest = hashlib.sha256()
            with (staging / dataset['filename']).open('w', encoding='utf-8', newline='') as output:
                writer = csv.writer(output)
                writer.writerow(dataset['columns'])
                for part in dataset['parts']:
                    part_count = 0
                    with (source / part['path']).open(encoding='utf-8-sig', newline='') as incoming:
                        reader = csv.reader(incoming)
                        if next(reader) != dataset['columns']:
                            raise ValueError('Column mismatch for ' + part['path'])
                        for row in reader:
                            if len(row) != len(dataset['columns']):
                                raise ValueError('Invalid row width in ' + part['path'])
                            writer.writerow(row)
                            digest.update(row_bytes(row))
                            count += 1
                            part_count += 1
                    if part_count != part['rows']:
                        raise ValueError('Part row count mismatch for ' + part['path'])
            if count != dataset['rows'] or digest.hexdigest() != dataset['logical_sha256']:
                raise ValueError('Reconstructed data check failed for ' + dataset['filename'])
            print(dataset['filename'], count, 'rows verified')

        # Move into the destination only after all three datasets pass checks.
        destination.mkdir(parents=True, exist_ok=True)
        for dataset in manifest['datasets']:
            shutil.move(str(staging / dataset['filename']), str(destination / dataset['filename']))
        for filename in ['refresh_1_method.json', 'refresh_2_method.json', 'demo_state.json']:
            shutil.copyfile(source / 'generation' / filename, destination / filename)
    print('Restored source folder:', destination)
    print('Set source_folder in your private config.json to this folder.')


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--destination', type=Path, default=ROOT / 'Project.Data.And.Results' / 'data' / 'demo_source')
    restore(parser.parse_args().destination)
