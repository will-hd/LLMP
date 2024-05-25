from run_llm_process import run_llm_process
from hf_api import get_model_and_tokenizer, llm_map
from parse_args import init_option_parser
from jsonargparse import ArgumentParser
import pickle


locations = ['GOOSE,NL',
    'GREENWOOD,NS',
    'ALERT,NU',
    'OTTAWA,ON',
    'COMOX,BC',
    'MONTREALPIERREELLIOTTT,QC',
    'KEYLAKE,SK',
    'RANFURLY2NW,AB',
    'YELLOWKNIFE,NT',
    'THOMPSON,MB',
    'SAINTJOHN,NB',
    'WHITEHORSE,YK',
    'CHARLOTTETOWN,PE']


def main():
    # parse the command line arguments
    parser = ArgumentParser()
    parser.add_argument('--llm_path', type=str, help='Path to LLM.')
    parser.add_argument('--batch_size', type=int, default=8)
    parser.add_argument("--llm_type", choices=llm_map.keys(), default="llama-2-7B",
                        help="Hugging face model to use.")
    parser.add_argument("--autoregressive", type=bool, default=True,
                        help="If true, append the previous prediction to the current prompt.")
    parser.add_argument("--max_generated_length",  type=int, default=12)
    parser.add_argument("--sort_x_test",  type=bool, default=True)
    parser.add_argument('--output_dir', type=str, default='./output/in_context',
                        help='Path to directory where output results are written.')
    parser.add_argument('--plot_dir', type=str, default='./plots/in_context',
                        help='Path to directory where output plots are written.')


    args = parser.parse_args()
    print(args, flush=True)

    option_parser = init_option_parser()

    model, tokenizer = get_model_and_tokenizer(args.llm_path, args.llm_type)
    for location in locations:
        data_path = './data/canada_precip/incontext_precip_{}.pkl'.format(location)
        # load the prompts which include the in-context examples
        with open(data_path, 'rb') as f:
            data = pickle.load(f)
        prompts = data['prompts']
        
        for key, prompt in prompts.items():
            config_args = option_parser.parse_args(args=[
                    "--experiment_name", "{}_in_context_{}_prompt_{}_auto_{}".format(args.llm_type, location, key, args.autoregressive),
                    "--data_path", data_path,
                    "--output_dir", args.output_dir,
                    "--plot_dir", args.plot_dir,
                    "--batch_size", str(args.batch_size),
                    "--prefix", prompt,
                    "--autoregressive", str(args.autoregressive),
                    "--max_generated_length", str(args.max_generated_length),
                    "--sort_x_test", str(args.sort_x_test),
                    "--num_samples", "30",
                    "--plot_trajectories", "5",
                    "--forecast", "True"
                    ])
            run_llm_process(args=config_args, model=model, tokenizer=tokenizer)


if __name__ == '__main__':
    main()
