import { HttpResponse, http } from "msw";

import { forwardBackendRequest } from "@/lib/backend-proxy";

import { server } from "./server";


const BACKEND_BASE_URL = "http://127.0.0.1:8000";

describe("forwardBackendRequest", () => {
  it("forwards GET requests with query params", async () => {
    server.use(
      http.get(`${BACKEND_BASE_URL}/recommendations`, ({ request }) => {
        const url = new URL(request.url);
        return HttpResponse.json({
          forwarded_path: url.pathname,
          limit: url.searchParams.get("limit"),
        });
      }),
    );

    const response = await forwardBackendRequest(
      new Request("http://localhost/api/backend/recommendations?limit=4"),
      ["recommendations"],
    );

    expect(response.status).toBe(200);
    await expect(response.json()).resolves.toEqual({
      forwarded_path: "/recommendations",
      limit: "4",
    });
  });

  it("forwards JSON mutation bodies and status codes", async () => {
    server.use(
      http.post(`${BACKEND_BASE_URL}/inventory`, async ({ request }) => {
        const payload = (await request.json()) as { name: string; quantity: number };
        return HttpResponse.json(
          {
            ...payload,
            id: 101,
          },
          { status: 201 },
        );
      }),
    );

    const response = await forwardBackendRequest(
      new Request("http://localhost/api/backend/inventory", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ name: "milk", quantity: 1 }),
      }),
      ["inventory"],
    );

    expect(response.status).toBe(201);
    await expect(response.json()).resolves.toEqual({ name: "milk", quantity: 1, id: 101 });
  });

  it("forwards multipart scan uploads", async () => {
    server.use(
      http.post(`${BACKEND_BASE_URL}/scan`, async ({ request }) => {
        const formData = await request.formData();
        const image = formData.get("image");
        return HttpResponse.json(
          {
            image_name: formData.get("image_name"),
            file_name: image && typeof image === "object" && "name" in image ? String(image.name) : null,
          },
          { status: 201 },
        );
      }),
    );

    const boundary = "----smart-meal-test-boundary";
    const multipartBody = [
      `--${boundary}`,
      'Content-Disposition: form-data; name="image_name"',
      "",
      "fridge.jpg",
      `--${boundary}`,
      'Content-Disposition: form-data; name="image"; filename="fridge.jpg"',
      "Content-Type: image/jpeg",
      "",
      "demo-image",
      `--${boundary}--`,
      "",
    ].join("\r\n");

    const response = await forwardBackendRequest(
      new Request("http://localhost/api/backend/scan", {
        method: "POST",
        headers: {
          "Content-Type": `multipart/form-data; boundary=${boundary}`,
        },
        body: multipartBody,
      }),
      ["scan"],
    );

    expect(response.status).toBe(201);
    await expect(response.json()).resolves.toEqual({
      image_name: "fridge.jpg",
      file_name: "fridge.jpg",
    });
  });
});
