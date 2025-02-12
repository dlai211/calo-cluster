import argparse

from calo_cluster.evaluation.experiments.base_experiment import BaseExperiment


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument('wandb_version')
    parser.add_argument('--ckpt_name')
    args = parser.parse_args()
    experiment = BaseExperiment(args.wandb_version, args.ckpt_name)
    experiment.save_predictions()


if __name__ == '__main__':
    main()
