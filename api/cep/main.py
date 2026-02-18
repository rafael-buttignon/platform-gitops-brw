from fastapi import FastAPI, HTTPException
import httpx

app = FastAPI(title="API de CEP")


@app.get("/")
async def root():
    return {"service": "api-cep", "status": "ok"}


@app.get("/health")
async def health():
    return {"status": "healthy"}


@app.get("/cep/{cep}")
async def consultar_cep(cep: str):
    cep = cep.replace("-", "").strip()
    if len(cep) != 8 or not cep.isdigit():
        raise HTTPException(status_code=400, detail="CEP inválido")

    url = f"https://viacep.com.br/ws/{cep}/json/"
    timeout = httpx.Timeout(8.0)
    try:
        async with httpx.AsyncClient(timeout=timeout) as client:
            resp = await client.get(url)
    except httpx.TimeoutException as exc:
        raise HTTPException(
            status_code=504,
            detail="Timeout ao consultar ViaCEP",
        ) from exc
    except httpx.HTTPError as exc:
        raise HTTPException(
            status_code=502,
            detail="Falha de rede ao consultar ViaCEP",
        ) from exc

    if resp.status_code != 200:
        raise HTTPException(status_code=502, detail="Falha ao consultar ViaCEP")

    data = resp.json()
    if data.get("erro"):
        raise HTTPException(status_code=404, detail="CEP não encontrado")

    return data
