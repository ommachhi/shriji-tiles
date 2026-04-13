import { render, screen } from "@testing-library/react";
import App from "./App";

jest.mock("axios", () => {
  const mockAxios = {
    get: jest.fn(),
    isCancel: jest.fn(() => false),
  };

  return {
    __esModule: true,
    default: mockAxios,
  };
});

test("renders the single search input", () => {
  render(<App />);

  expect(
    screen.getByRole("heading", { name: /multi catalog product search/i })
  ).toBeInTheDocument();

  expect(
    screen.getByPlaceholderText(/enter product code or product name/i)
  ).toBeInTheDocument();
});
