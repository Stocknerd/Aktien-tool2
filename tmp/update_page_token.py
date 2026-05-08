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
        f.write('PAGE_TOKEN=EAAVGjnfVF0YBRdNH0cmqZA21ooKIez1EGqZAyUyH42ZAxHQARC8OYAzi9tn2nTyDdZCKaRlEc1rNgfm9CL9pIXOSMYGNaASZBtsyI44QFZC03wKvxK2LIMOJiXBvhnujAzwYmwqBVfVyJGtxK41AjZCZCLjPusCqwAVPy6B8AUsIBBzSeZBZCCvcHb54ZBut4GOAPysYkDXdN0D3MBYFGZCEF4dH\n')
        
    print("Remote ENV updated with PAGE_TOKEN.")

if __name__ == '__main__':
    update_env()
