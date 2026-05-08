import os

def update_env():
    p = '/home/ubuntu/aktien-tool2/.env'
    lines = []
    if os.path.exists(p):
        with open(p, 'r') as f:
            lines = f.readlines()
    
    with open(p, 'w') as f:
        for l in lines:
            if not l.startswith('PAGE_TOKEN='):
                f.write(l)
        f.write('PAGE_TOKEN=EAAVGjnfVF0YBRfsPe7zRyk80G17xPcroaSZB8vutCenPCpqm48J8ANZBtIZAxQelwuqPhX30sYxFOK1hN0bqD0xGXj3GbNKkT2lmgpLbFuCZChLUVROplZCzyZBmeAXdwd9ZAQdwyZAyjKOdKGQ3uFgf3DDX40121cYWtpTSm60KZBhn1pTqLYEOO8cbEuVgjP0BZBo4vlORMtmnDDFlLB\n')
        
    print("Remote ENV updated successfully.")

if __name__ == '__main__':
    update_env()
