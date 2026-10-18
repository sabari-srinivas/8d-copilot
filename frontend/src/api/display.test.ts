import { describe, expect, it } from "vitest";
import { plainName } from "./display";

describe("plainName", () => {
  it("drops the qualifier the plant and customer names carry", () => {
    expect(plainName("Hoshino Denso (fictional)")).toBe("Hoshino Denso");
    expect(plainName("Sree Electronics (fictional), Chennai")).toBe(
      "Sree Electronics, Chennai",
    );
  });

  it("leaves a name that never carried it alone", () => {
    expect(plainName("Meridian Auto Electronics")).toBe("Meridian Auto Electronics");
  });

  it("is case insensitive and accepts the longer spelling", () => {
    expect(plainName("Kaveri Motors (Fictional)")).toBe("Kaveri Motors");
    expect(plainName("Araku Components (fictitious)")).toBe("Araku Components");
  });

  it("does not leave a double space behind a mid-string removal", () => {
    // The qualifier sits mid-name in the plant string, so removing it naively would
    // leave "Sree Electronics  , Chennai" — visible in the header on every screen.
    expect(plainName("Acme (fictional) Industries")).toBe("Acme Industries");
  });

  it("leaves an unrelated parenthetical in place", () => {
    expect(plainName("Toyota (Japan) KK")).toBe("Toyota (Japan) KK");
  });

  it("handles an empty string without throwing", () => {
    expect(plainName("")).toBe("");
  });
});
