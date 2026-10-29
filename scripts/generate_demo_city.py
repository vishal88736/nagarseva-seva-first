"""Write a reproducible fictional city. This is Demo data, never public records."""
import argparse,json,sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'nagarseva'))
from model.api.civic_demo import seed_demo,validate_workspace

def main():
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--seed',type=int,default=96);parser.add_argument('--count',type=int,default=100);parser.add_argument('--output',type=Path,required=True);args=parser.parse_args()
    state=seed_demo(args.seed,args.count);validate_workspace(state)
    args.output.parent.mkdir(parents=True,exist_ok=True);args.output.write_text(json.dumps({'notice':'Demo data',**state},ensure_ascii=False,indent=2)+'\n')
    print(f'Demo data: {len(state["settlements"])} fictional settlements, {len(state["wards"])} fictional wards; validation passed.')
if __name__=='__main__':main()
