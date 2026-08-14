import { fireEvent, render, screen } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";

import { PostCard } from "./PostCard";

const post = {
  id: "post-1", title: "如何构建可靠的 RAG 检索？", type: "question" as const,
  tags: ["RAG"], voteCount: 10, viewCount: 20, replyCount: 2,
  isFolded: false, createdAt: new Date().toISOString(), updatedAt: new Date().toISOString(),
  author: { id: "user-1", username: "tester", avatar: null },
  board: { id: "board-1", name: "RAG", tier: "deep" as const },
};

describe("PostCard", () => {
  it("tracks a recommendation open from the title", async () => {
    const onOpen = vi.fn();
    render(<PostCard post={post} onOpen={onOpen} />);
    const link = screen.getByRole("link", { name: post.title });
    link.addEventListener("click", (event) => event.preventDefault());
    fireEvent.click(link);
    expect(onOpen).toHaveBeenCalledWith(post);
  });

  it("hides folded content", () => {
    render(<PostCard post={{ ...post, isFolded: true }} />);
    expect(screen.getByText("该内容因被举报已折叠")).toBeInTheDocument();
    expect(screen.queryByText(post.title)).not.toBeInTheDocument();
  });
});
